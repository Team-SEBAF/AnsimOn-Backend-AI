from typing import List, Optional

from pydantic import BaseModel, Field

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


class OCRTableWord(BaseModel):
    text: str
    confidence: Optional[float] = None
    vertices: Optional[List[OCRVertex]] = None


class OCRTableLine(BaseModel):
    text: str
    confidence: Optional[float] = None
    vertices: Optional[List[OCRVertex]] = None
    words: List[OCRTableWord] = Field(default_factory=list)


class OCRTableCell(BaseModel):
    text: str
    row_index: int
    column_index: int
    row_span: int = 1
    column_span: int = 1
    confidence: Optional[float] = None
    vertices: Optional[List[OCRVertex]] = None
    lines: List[OCRTableLine] = Field(default_factory=list)


class OCRTable(BaseModel):
    text: str = ""
    confidence: Optional[float] = None
    vertices: Optional[List[OCRVertex]] = None
    cells: List[OCRTableCell] = Field(default_factory=list)

class OCRResult(BaseModel):
    full_text: str
    segments: List[OCRSegment]
    language: Optional[str] = None
    engine: str
    tables: List[OCRTable] = Field(default_factory=list)
