from __future__ import annotations

from .types import OCRResult, OCRSegment

def assign_speaker_sides(ocr_result: OCRResult) -> OCRResult:
    candidates = [segment for segment in ocr_result.segments if segment.center_x is not None]
    if not candidates:
        return ocr_result

    min_x = min(segment.min_x for segment in candidates if segment.min_x is not None)
    max_x = max(segment.max_x for segment in candidates if segment.max_x is not None)
    width = max_x - min_x
    if width <= 0:
        return ocr_result

    center_line = min_x + (width / 2.0)
    dead_zone = max(width * 0.1, 60.0)

    assigned_segments: list[OCRSegment] = []
    for segment in ocr_result.segments:
        side = _infer_segment_side(
            segment,
            center_line=center_line,
            dead_zone=dead_zone,
        )
        assigned_segments.append(segment.model_copy(update={"speaker_side": side}))

    return ocr_result.model_copy(update={"segments": assigned_segments})

def _infer_segment_side(
    segment: OCRSegment,
    *,
    center_line: float,
    dead_zone: float,
) -> str:
    center_x = segment.center_x
    if center_x is None:
        return "unknown"

    if center_x <= center_line - dead_zone:
        return "left"
    if center_x >= center_line + dead_zone:
        return "right"
    return "unknown"