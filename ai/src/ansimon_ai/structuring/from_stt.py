from datetime import datetime
from typing import Optional

from ansimon_ai.stt.types import STTResult
from .types import StructuringInput, StructuringSegment
from .timestamp_utils import extract_timestamp

def build_structuring_input_from_stt(
    stt: STTResult,
    metadata_fallback_timestamp: Optional[datetime] = None,
) -> StructuringInput:
    return StructuringInput(
        modality="text",
        source_type="stt",
        language=stt.language,
        full_text=stt.full_text,
        segments=[
            StructuringSegment(
                text=seg.text,
                start=seg.start,
                end=seg.end,
                speaker=seg.speaker,
                timestamp=extract_timestamp(seg.text, fallback=metadata_fallback_timestamp),
            )
            for seg in stt.segments
        ],
    )