import base64
import os
import time
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from .layout import assign_speaker_sides
from .types import OCRResult, OCRSegment, OCRVertex

def clova_ocr_image_to_result(
    image_path: str,
    *,
    invoke_url: Optional[str] = None,
    secret: Optional[str] = None,
    lang: str = "ko",
) -> OCRResult:
    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        load_dotenv = None

    if load_dotenv is not None:
        load_dotenv()

    resolved_invoke_url = invoke_url or os.getenv("CLOVA_OCR_INVOKE_URL")
    resolved_secret = secret or os.getenv("CLOVA_OCR_SECRET")

    if not resolved_invoke_url:
        raise ValueError("CLOVA_OCR_INVOKE_URL is required.")
    if not resolved_secret:
        raise ValueError("CLOVA_OCR_SECRET is required.")

    request_url = _resolve_general_url(resolved_invoke_url)
    file_path = Path(image_path)
    image_bytes = file_path.read_bytes()
    image_format = _infer_image_format(file_path)

    payload = {
        "version": "V2",
        "requestId": str(uuid4()),
        "timestamp": int(time.time() * 1000),
        "lang": lang,
        "images": [
            {
                "format": image_format,
                "name": file_path.name,
                "data": base64.b64encode(image_bytes).decode("ascii"),
            }
        ],
    }

    try:
        import requests
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("requests is required for CLOVA OCR integration.") from exc

    response = requests.post(
        request_url,
        headers={
            "Content-Type": "application/json",
            "X-OCR-SECRET": resolved_secret,
        },
        json=payload,
        timeout=30,
    )
    response.raise_for_status()

    return _parse_clova_ocr_response(response.json())

def _resolve_general_url(invoke_url: str) -> str:
    normalized = invoke_url.rstrip("/")
    if normalized.endswith("/general"):
        return normalized
    return f"{normalized}/general"

def _infer_image_format(path: Path) -> str:
    mapping = {
        ".jpg": "jpg",
        ".jpeg": "jpg",
        ".png": "png",
        ".pdf": "pdf",
        ".tif": "tiff",
        ".tiff": "tiff",
        ".bmp": "bmp",
        ".webp": "webp",
    }
    suffix = path.suffix.lower()
    if suffix not in mapping:
        raise ValueError(f"Unsupported image format for CLOVA OCR: {suffix}")
    return mapping[suffix]

def _parse_clova_ocr_response(data: dict[str, Any]) -> OCRResult:
    images = data.get("images")
    if not isinstance(images, list) or not images:
        raise ValueError("CLOVA OCR response does not contain images.")

    first_image = images[0]
    fields = first_image.get("fields")
    if not isinstance(fields, list):
        raise ValueError("CLOVA OCR response does not contain fields.")

    segments: list[OCRSegment] = []
    tokens: list[str] = []
    vertices: list[OCRVertex] = []
    line_no = 1

    for field in fields:
        if not isinstance(field, dict):
            continue

        text = str(field.get("inferText") or "").strip()
        if not text:
            continue

        tokens.append(text)
        vertices.extend(_parse_vertices(field))

        if field.get("lineBreak"):
            segments.append(
                OCRSegment(
                    text=" ".join(tokens).strip(),
                    page=1,
                    line=line_no,
                    line_break=True,
                    vertices=vertices or None,
                )
            )
            line_no += 1
            tokens = []
            vertices = []

    if tokens:
        segments.append(
            OCRSegment(
                text=" ".join(tokens).strip(),
                page=1,
                line=line_no,
                line_break=False,
                vertices=vertices or None,
            )
        )

    full_text = "\n".join(segment.text for segment in segments).strip()
    if not full_text:
        full_text = str(first_image.get("inferText") or "").strip()

    result = OCRResult(
        full_text=full_text,
        segments=segments,
        language=data.get("lang") or "ko",
        engine="clova:v2",
    )
    return assign_speaker_sides(result)

def _parse_vertices(field: dict[str, Any]) -> list[OCRVertex]:
    bounding_poly = field.get("boundingPoly")
    if not isinstance(bounding_poly, dict):
        return []

    raw_vertices = bounding_poly.get("vertices")
    if not isinstance(raw_vertices, list):
        return []

    vertices: list[OCRVertex] = []
    for vertex in raw_vertices:
        if not isinstance(vertex, dict):
            continue
        x = vertex.get("x")
        y = vertex.get("y")
        if x is None or y is None:
            continue
        vertices.append(OCRVertex(x=float(x), y=float(y)))
    return vertices