from typing import Literal, Optional
from pydantic import BaseModel

class EvidenceTag(BaseModel):
    tag: Literal[
        "ANCHOR_OK",
        "ANCHOR_NOT_FOUND",
        "ANCHOR_AMBIGUOUS",
        "STRUCT_VALID",
        "STRUCT_INVALID",
        "CONFIDENCE_PRESENT",
        "CONFIDENCE_WITHOUT_ANCHOR",
    ]
    source: Literal["anchor", "structure", "confidence"]
    note: Optional[str] = None