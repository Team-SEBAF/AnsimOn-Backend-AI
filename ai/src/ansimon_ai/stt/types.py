from pydantic import BaseModel
from typing import List, Optional

class STTSegment(BaseModel):
    start: float
    end: float
    text: str

class STTResult(BaseModel):
    full_text: str
    segments: List[STTSegment]
    language: Optional[str] = None
    engine: str