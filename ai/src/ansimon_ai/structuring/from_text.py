from datetime import datetime
from typing import Optional

from .types import StructuringInput, StructuringSegment
from .timestamp_utils import extract_timestamp

def build_structuring_input_from_text(
    text: str,
    metadata_fallback_timestamp: Optional[datetime] = None,
) -> StructuringInput:
    return StructuringInput(
        modality="text",
        source_type="text",
        language=None,
        full_text=text,
        segments=[
            StructuringSegment(
                text=text,
                start=0.0,
                end=0.0,
                timestamp=extract_timestamp(text, fallback=metadata_fallback_timestamp),
            )
        ],
    )