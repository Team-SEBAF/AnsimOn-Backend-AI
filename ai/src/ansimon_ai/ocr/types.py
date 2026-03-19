from pydantic import BaseModel
from typing import List, Optional

class OCRSegment(BaseModel):
    text: str
    page: Optional[int] = None
    line: Optional[int] = None
    start: Optional[float] = None
    end: Optional[float] = None

class OCRResult(BaseModel):
    full_text: str
    segments: List[OCRSegment]
    language: Optional[str] = None
    engine: str