import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image as PILImage

from .types import OCRResult
from .types import OCRSegment
from .clova_ocr import clova_ocr_image_to_result
from .table_formatting import format_ocr_result_text, is_tabular_table

from ansimon_ai.structuring.types import StructuringInput, StructuringSegment
from ansimon_ai.structuring.timestamp_utils import extract_timestamp

ImageInput = str | Path | PILImage.Image

_UI_EDGE_CHARS = "<>=_+-@…·|~ "
_UI_ONLY_VALUES = {"글", "메시지 입력", "message"}
_TIME_ONLY_PATTERN = re.compile(r"^(?:(?:오전|오후)\s*)?\d{1,2}:\d{2}$")
_DATE_ONLY_PATTERN = re.compile(r"^\d{4}\s*[./년-]\s*\d{1,2}\s*[./월-]\s*\d{1,2}")

def _clean_ocr_text(text: str) -> str:
    text = " ".join(text.replace("\n", " ").replace("\r", " ").split())
    text = text.strip()
    if not text:
        return ""

    if all(c in "!@#$%^&*()_+=[]{}|;:'\",.<>?/\\-~…· " for c in text):
        return ""

    text = text.strip(_UI_EDGE_CHARS)
    if not text:
        return ""

    parts = text.split()
    while len(parts) > 1 and parts[-1] == "Q":
        parts.pop()
    text = " ".join(parts).strip(_UI_EDGE_CHARS)

    if text.lower() in _UI_ONLY_VALUES:
        return ""

    return text

def preprocess_ocr_segments(segments):
    processed = []
    for seg in segments:
        raw_text = _clean_ocr_text(seg.text)
        if not raw_text:
            continue
        text = raw_text
        if not _is_time_only_text(raw_text):
            text = _apply_speaker_prefix(text, seg.speaker_side)
        start = seg.start if seg.start is not None else 0.0
        end = seg.end if seg.end is not None else 0.0
        processed.append(
            {
                **seg.model_dump(),
                "text": text,
                "raw_text": raw_text,
                "start": start,
                "end": end,
            }
        )
    return _merge_time_segments(processed)

def _merge_time_segments(segments):
    merged = []
    pending_time_text = None
    for seg in segments:
        raw_text = seg.get("raw_text") or seg.get("text", "")
        if _is_time_only_text(raw_text):
            target = _find_time_attachment_target(merged)
            if target is not None:
                target["text"] = f'{target["text"]} [시각: {raw_text}]'
            else:
                pending_time_text = raw_text
            continue

        if pending_time_text and not _is_date_only_text(raw_text):
            seg["text"] = f'{seg["text"]} [시각: {pending_time_text}]'
            pending_time_text = None

        merged.append(seg)
    return merged

def _find_time_attachment_target(segments):
    for seg in reversed(segments):
        raw_text = seg.get("raw_text") or seg.get("text", "")
        if _is_date_only_text(raw_text):
            continue
        return seg
    return None

def _is_time_only_text(text: str) -> bool:
    return bool(_TIME_ONLY_PATTERN.fullmatch(text.strip()))

def _is_date_only_text(text: str) -> bool:
    return bool(_DATE_ONLY_PATTERN.match(text.strip()))

def _apply_speaker_prefix(text: str, speaker_side: Optional[str]) -> str:
    if speaker_side == "left":
        return f"[상대방] {text}"
    if speaker_side == "right":
        return f"[피해자] {text}"
    return text

def build_structuring_input_from_ocr(
    ocr: OCRResult,
    metadata_fallback_timestamp: Optional[datetime] = None,
) -> StructuringInput:
    segments = preprocess_ocr_segments(ocr.segments)
    full_text = _build_ocr_full_text(ocr, segments)
    return StructuringInput(
        modality="text",
        source_type="ocr",
        language=ocr.language,
        full_text=full_text or ocr.full_text,
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

def _build_ocr_full_text(ocr: OCRResult, segments: list[dict]) -> str:
    if any(is_tabular_table(table) for table in ocr.tables):
        formatted_text = format_ocr_result_text(ocr).strip()
        if formatted_text:
            return formatted_text

    processed_text = "\n".join(seg.get("text", "") for seg in segments).strip()
    return processed_text or ocr.full_text

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

def tesseract_ocr_image_to_result(
    image_input: ImageInput,
    *,
    lang: str = "kor+eng",
) -> OCRResult:
    import pytesseract

    tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.name == "nt" and os.path.exists(tesseract_cmd):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    image = _load_image_input(image_input)
    variants = _prepare_ocr_variants(image)

    best_result: OCRResult | None = None
    best_score = -1

    for variant_name, variant_image, config in variants:
        result = _run_ocr_variant(
            pytesseract,
            pytesseract.Output,
            variant_image,
            lang=lang,
            config=config,
            engine_name=f"tesseract:{variant_name}",
        )
        score = _score_ocr_result(result)
        if score > best_score:
            best_score = score
            best_result = result

    assert best_result is not None
    return best_result

def ocr_image_to_result(
    image_input: ImageInput,
    *,
    engine: Optional[str] = None,
    lang: Optional[str] = None,
) -> OCRResult:
    resolved_engine = _resolve_ocr_engine(engine)
    if resolved_engine == "clova":
        if lang is None:
            return clova_ocr_image_to_result(image_input)
        return clova_ocr_image_to_result(image_input, lang=_normalize_clova_lang(lang))
    if resolved_engine == "tesseract":
        if lang is None:
            return tesseract_ocr_image_to_result(image_input)
        return tesseract_ocr_image_to_result(image_input, lang=lang)
    raise ValueError(f"Unsupported OCR engine: {resolved_engine}")

def _load_image_input(image_input: ImageInput) -> PILImage.Image:
    if isinstance(image_input, PILImage.Image):
        return image_input.copy()

    with PILImage.open(image_input) as image:
        return image.copy()

def _normalize_clova_lang(lang: str) -> str:
    token = lang.split("+", 1)[0].strip().lower()
    mapping = {
        "ko": "ko",
        "kor": "ko",
        "en": "en",
        "eng": "en",
        "ja": "ja",
        "jpn": "ja",
    }
    return mapping.get(token, token)

def _resolve_ocr_engine(engine: Optional[str]) -> str:
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        load_dotenv = None

    if load_dotenv is not None:
        load_dotenv()

    return (engine or os.getenv("OCR_ENGINE") or "tesseract").strip().lower()