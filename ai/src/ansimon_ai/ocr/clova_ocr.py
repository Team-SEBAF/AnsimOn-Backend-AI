import base64
import os
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from PIL import Image as PILImage

from .layout import assign_speaker_sides
from .types import OCRResult, OCRSegment, OCRTable, OCRTableCell, OCRTableLine, OCRTableWord, OCRVertex

ImageInput = str | Path | PILImage.Image
_TABLE_DETECTION_DISABLED_CODE = "0028"

def clova_ocr_image_to_result(
    image_input: ImageInput,
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
    image_bytes, image_format, image_name = _read_image_input(image_input)

    payload = {
        "version": "V2",
        "requestId": str(uuid4()),
        "timestamp": int(time.time() * 1000),
        "lang": lang,
        "enableTableDetection": True,
        "images": [
            {
                "format": image_format,
                "name": image_name,
                "data": base64.b64encode(image_bytes).decode("ascii"),
            }
        ],
    }

    try:
        import requests
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError("requests is required for CLOVA OCR integration.") from exc

    headers = {
        "Content-Type": "application/json",
        "X-OCR-SECRET": resolved_secret,
    }
    response = _post_clova_request(
        requests,
        request_url,
        headers=headers,
        payload=payload,
    )

    return _parse_clova_ocr_response(response.json())


def _post_clova_request(requests_module, request_url: str, *, headers: dict[str, str], payload: dict[str, Any]):
    response = requests_module.post(
        request_url,
        headers=headers,
        json=payload,
        timeout=30,
    )

    try:
        response.raise_for_status()
        return response
    except requests_module.HTTPError:
        if payload.get("enableTableDetection") and _is_table_detection_disabled_response(response):
            fallback_payload = dict(payload)
            fallback_payload["enableTableDetection"] = False
            fallback_response = requests_module.post(
                request_url,
                headers=headers,
                json=fallback_payload,
                timeout=30,
            )
            fallback_response.raise_for_status()
            return fallback_response
        raise

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

def _read_image_input(image_input: ImageInput) -> tuple[bytes, str, str]:
    if isinstance(image_input, PILImage.Image):
        buffer = BytesIO()
        image_input.save(buffer, format="PNG")
        return buffer.getvalue(), "png", "image.png"

    file_path = Path(image_input)
    return file_path.read_bytes(), _infer_image_format(file_path), file_path.name

def _parse_clova_ocr_response(data: dict[str, Any]) -> OCRResult:
    images = data.get("images")
    if not isinstance(images, list) or not images:
        raise ValueError("CLOVA OCR response does not contain images.")

    first_image = images[0]
    fields = first_image.get("fields")
    if not isinstance(fields, list):
        raise ValueError("CLOVA OCR response does not contain fields.")
    tables = _parse_tables(first_image.get("tables"))

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
        tables=tables,
    )
    return assign_speaker_sides(result)


def _is_table_detection_disabled_response(response) -> bool:
    try:
        data = response.json()
    except ValueError:
        data = None

    if not isinstance(data, dict):
        return _TABLE_DETECTION_DISABLED_CODE in (getattr(response, "text", "") or "")

    code_candidates: list[str] = []
    for key in ("code", "statusCode"):
        value = data.get(key)
        if value is not None:
            code_candidates.append(str(value))

    for nested_key in ("status", "error"):
        nested = data.get(nested_key)
        if isinstance(nested, dict):
            value = nested.get("code")
            if value is not None:
                code_candidates.append(str(value))

    if _TABLE_DETECTION_DISABLED_CODE in code_candidates:
        return True

    messages = [str(data.get("message") or "")]
    for nested_key in ("status", "error"):
        nested = data.get(nested_key)
        if isinstance(nested, dict):
            messages.append(str(nested.get("message") or ""))

    return any("Table detection disabled" in message for message in messages)


def _parse_tables(raw_tables: Any) -> list[OCRTable]:
    if not isinstance(raw_tables, list):
        return []

    tables: list[OCRTable] = []
    for raw_table in raw_tables:
        if not isinstance(raw_table, dict):
            continue

        cells: list[OCRTableCell] = []
        raw_cells = raw_table.get("cells")
        if isinstance(raw_cells, list):
            for raw_cell in raw_cells:
                cell = _parse_table_cell(raw_cell)
                if cell is not None:
                    cells.append(cell)

        tables.append(
            OCRTable(
                text=str(raw_table.get("inferText") or "").strip(),
                confidence=_to_float(raw_table.get("inferConfidence")),
                vertices=_parse_vertices(raw_table),
                cells=cells,
            )
        )

    return tables


def _parse_table_cell(raw_cell: Any) -> OCRTableCell | None:
    if not isinstance(raw_cell, dict):
        return None

    lines = _parse_table_lines(raw_cell.get("cellTextLines"))
    text = _extract_table_cell_text(raw_cell, lines)
    if not text:
        return None

    return OCRTableCell(
        text=text,
        row_index=_to_int(raw_cell.get("rowIndex"), default=0),
        column_index=_to_int(raw_cell.get("columnIndex"), default=0),
        row_span=max(_to_int(raw_cell.get("rowSpan"), default=1), 1),
        column_span=max(_to_int(raw_cell.get("columnSpan"), default=1), 1),
        confidence=_to_float(raw_cell.get("inferConfidence")),
        vertices=_parse_vertices(raw_cell),
        lines=lines,
    )


def _parse_table_lines(raw_lines: Any) -> list[OCRTableLine]:
    if not isinstance(raw_lines, list):
        return []

    lines: list[OCRTableLine] = []
    for raw_line in raw_lines:
        if not isinstance(raw_line, dict):
            continue

        words = _parse_table_words(raw_line.get("cellWords"))
        text = " ".join(word.text for word in words).strip()
        if not text:
            continue

        lines.append(
            OCRTableLine(
                text=text,
                confidence=_to_float(raw_line.get("inferConfidence")),
                vertices=_parse_vertices(raw_line),
                words=words,
            )
        )

    return lines


def _parse_table_words(raw_words: Any) -> list[OCRTableWord]:
    if not isinstance(raw_words, list):
        return []

    words: list[OCRTableWord] = []
    for raw_word in raw_words:
        if not isinstance(raw_word, dict):
            continue

        text = str(raw_word.get("inferText") or "").strip()
        if not text:
            continue

        words.append(
            OCRTableWord(
                text=text,
                confidence=_to_float(raw_word.get("inferConfidence")),
                vertices=_parse_vertices(raw_word),
            )
        )

    return words


def _extract_table_cell_text(raw_cell: dict[str, Any], lines: list[OCRTableLine]) -> str:
    line_text = "\n".join(line.text for line in lines if line.text).strip()
    if line_text:
        return line_text
    return str(raw_cell.get("inferText") or "").strip()


def _to_int(value: Any, *, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None

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
