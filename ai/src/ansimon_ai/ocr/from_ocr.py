import os
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
        text = text.replace("\n", " ").replace("\r", " ").replace("  ", " ")
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

def ocr_image_to_result(image_path: str) -> OCRResult:
    import pytesseract
    from PIL import Image

    tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.name == "nt" and os.path.exists(tesseract_cmd):
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img, lang="kor")
    segments = [
        OCRSegment(text=line.strip())
        for line in text.splitlines() if line.strip()
    ]
    return OCRResult(
        full_text=text,
        segments=segments,
        language="ko",
        engine="tesseract"
    )