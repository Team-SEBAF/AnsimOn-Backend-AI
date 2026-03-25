import os
import re
from datetime import datetime
from typing import Optional

from .types import OCRResult
from .types import OCRSegment

from ansimon_ai.structuring.types import StructuringInput, StructuringSegment
from ansimon_ai.structuring.timestamp_utils import extract_timestamp

def preprocess_ocr_segments(segments):
    processed = []
    for seg in segments:
        text = seg.text.strip()
        if not text or all(c in "!@#$%^&*()_+=[]{}|;:'\",.<>?/\\ " for c in text):
            continue
        text = " ".join(text.replace("\n", " ").replace("\r", " ").split())
        start = seg.start if seg.start is not None else 0.0
        end = seg.end if seg.end is not None else 0.0
        processed.append({**seg.model_dump(), "text": text, "start": start, "end": end})
    return processed

def build_structuring_input_from_ocr(
    ocr: OCRResult,
    metadata_fallback_timestamp: Optional[datetime] = None,
) -> StructuringInput:
    segments = preprocess_ocr_segments(ocr.segments)
    return StructuringInput(
        modality="text",
        source_type="ocr",
        language=ocr.language,
        full_text=ocr.full_text,
        segments=[
            StructuringSegment(
                text=seg.get("text", ""),
                start=seg.get("start") if seg.get("start") is not None else 0.0,
                end=seg.get("end") if seg.get("end") is not None else 0.0,
                timestamp=extract_timestamp(
                    seg.get("text", ""),
                    fallback=metadata_fallback_timestamp,
                ),
            )
            for seg in segments
        ],
    )

def _prepare_ocr_variants(image):
    from PIL import ImageFilter, ImageOps

    variants = []

    variants.append(("original_sparse", image, "--oem 3 --psm 11"))

    gray = ImageOps.grayscale(image)
    enhanced = ImageOps.autocontrast(gray)
    enhanced = enhanced.resize((enhanced.width * 2, enhanced.height * 2))
    enhanced = enhanced.filter(ImageFilter.SHARPEN)
    variants.append(("enhanced_sparse", enhanced, "--oem 3 --psm 11"))

    binary = ImageOps.autocontrast(gray)
    binary = binary.resize((binary.width * 3, binary.height * 3))
    binary = binary.point(lambda p: 255 if p > 180 else 0)
    binary = binary.filter(ImageFilter.SHARPEN)
    variants.append(("binary_block", binary, "--oem 3 --psm 6"))

    return variants

def _extract_segments_from_data(data) -> list[OCRSegment]:
    grouped: dict[tuple[int, int, int, int], list[str]] = {}

    count = len(data.get("text", []))
    for idx in range(count):
        text = (data["text"][idx] or "").strip()
        if not text:
            continue

        key = (
            int(data.get("page_num", [1] * count)[idx]),
            int(data.get("block_num", [0] * count)[idx]),
            int(data.get("par_num", [0] * count)[idx]),
            int(data.get("line_num", [0] * count)[idx]),
        )
        grouped.setdefault(key, []).append(text)

    segments: list[OCRSegment] = []
    for (page_num, _block_num, _par_num, line_num), parts in grouped.items():
        line_text = " ".join(parts).strip()
        if not line_text:
            continue
        segments.append(
            OCRSegment(
                text=line_text,
                page=page_num,
                line=line_num,
            )
        )

    return segments

def _score_ocr_result(result: OCRResult) -> int:
    text = result.full_text or ""
    score = len(text)

    score += len(re.findall(r"\d{4}[-./년]\s*\d{1,2}", text)) * 20
    score += len(re.findall(r"(오전|오후)?\s*\d{1,2}:\d{2}", text)) * 30
    score += len(re.findall(r"[가-힣]{2,}", text)) * 2

    if "오전" in text or "오후" in text:
        score += 40

    return score

def _run_ocr_variant(pytesseract, output_cls, image, *, lang: str, config: str, engine_name: str) -> OCRResult:
    data = pytesseract.image_to_data(
        image,
        lang=lang,
        config=config,
        output_type=output_cls.DICT,
    )
    segments = _extract_segments_from_data(data)

    if segments:
        full_text = "\n".join(seg.text for seg in segments)
    else:
        full_text = pytesseract.image_to_string(image, lang=lang, config=config)
        segments = [OCRSegment(text=line.strip()) for line in full_text.splitlines() if line.strip()]

    return OCRResult(
        full_text=full_text,
        segments=segments,
        language="ko",
        engine=engine_name,
    )

def ocr_image_to_result(image_path: str) -> OCRResult:
    import pytesseract
    from PIL import Image

    tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.name == "nt" and os.path.exists(tesseract_cmd):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    image = Image.open(image_path)
    variants = _prepare_ocr_variants(image)

    best_result: OCRResult | None = None
    best_score = -1

    for variant_name, variant_image, config in variants:
        result = _run_ocr_variant(
            pytesseract,
            pytesseract.Output,
            variant_image,
            lang="kor+eng",
            config=config,
            engine_name=f"tesseract:{variant_name}",
        )
        score = _score_ocr_result(result)
        if score > best_score:
            best_score = score
            best_result = result

    assert best_result is not None
    return best_result