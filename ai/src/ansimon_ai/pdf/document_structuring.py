from datetime import datetime
from typing import List, Optional
from ..structuring.types import StructuringInput, StructuringSegment
from ..structuring.timestamp_utils import extract_timestamp

def build_structuring_input_from_document(
    texts: List[str],
    metadata_fallback_timestamp: Optional[datetime] = None,
) -> StructuringInput:
    segments = []
    for line in texts:
        segments.append(
            StructuringSegment(
                text=line,
                start=0.0,
                end=0.0,
                timestamp=extract_timestamp(line, fallback=metadata_fallback_timestamp),
            )
        )
    return StructuringInput(
        modality="text",
        source_type="document",
        language=None,
        full_text="\n".join(texts),
        segments=segments
    )