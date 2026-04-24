from pydantic import BaseModel
from typing import List, Optional

class OCRVertex(BaseModel):
    x: float
    y: float

class OCRSegment(BaseModel):
    text: str
    page: Optional[int] = None
    line: Optional[int] = None
    start: Optional[float] = None
    end: Optional[float] = None
    line_break: Optional[bool] = None
    vertices: Optional[List[OCRVertex]] = None
    speaker_side: Optional[str] = None

    @property
    def min_x(self) -> Optional[float]:
        if not self.vertices:
            return None
        return min(vertex.x for vertex in self.vertices)

    @property
    def max_x(self) -> Optional[float]:
        if not self.vertices:
            return None
        return max(vertex.x for vertex in self.vertices)

    @property
    def center_x(self) -> Optional[float]:
        if self.min_x is None or self.max_x is None:
            return None
        return (self.min_x + self.max_x) / 2.0

    @property
    def min_y(self) -> Optional[float]:
        if not self.vertices:
            return None
        return min(vertex.y for vertex in self.vertices)

    @property
    def max_y(self) -> Optional[float]:
        if not self.vertices:
            return None
        return max(vertex.y for vertex in self.vertices)

    @property
    def center_y(self) -> Optional[float]:
        if self.min_y is None or self.max_y is None:
            return None
        return (self.min_y + self.max_y) / 2.0

class OCRResult(BaseModel):
    full_text: str
    segments: List[OCRSegment]
    language: Optional[str] = None
    engine: str