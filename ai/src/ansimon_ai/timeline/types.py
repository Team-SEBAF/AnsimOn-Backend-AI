from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

EvidenceType = Literal[
    "MESSAGE",
    "VOICE",
    "VICTIM",
    "REPORT_RECORD",
    "INCIDENT_LOG",
]

FileFormat = Literal[
    "IMAGE",
    "AUDIO",
    "VIDEO",
    "PDF",
    "HWP",
    "DOCX",
    "TXT",
]

EvidenceProcessingStatus = Literal["completed", "skipped", "failed"]

TimelineTagType = Literal[
    "repeat",
    "physical",
    "threat",
    "sexual_insult",
    "refusal",
]

class IncidentLogFormInput(BaseModel):
    title: str
    date: str
    time: str
    place: str
    situation: str

class TimelinePrototypeEvidenceInput(BaseModel):
    evidence_id: UUID
    type: EvidenceType
    file_format: Optional[FileFormat] = None
    file_name: Optional[str] = None
    file_bytes: Optional[bytes] = None
    extracted_text: Optional[str] = None
    incident_log_form: Optional[IncidentLogFormInput] = None

class TimelinePrototypeAiInput(BaseModel):
    complaint_id: UUID
    evidences: List[TimelinePrototypeEvidenceInput]

class EvidenceProcessingResult(BaseModel):
    evidence_id: UUID
    type: EvidenceType
    status: EvidenceProcessingStatus
    source_type: Optional[Literal["ocr", "stt", "document", "form"]] = None
    normalized_text: Optional[str] = None
    structured_data: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[TimelineTagType] = Field(default_factory=list)
    error_code: Optional[str] = None
    error_message: Optional[str] = None

class TimelineEvidenceItem(BaseModel):
    timeline_evidence_id: UUID
    index: int
    title: str
    description: str
    tags: List[TimelineTagType]
    referenced_evidence_count: int = 1
    referenced_evidence_ids: List[UUID] = Field(default_factory=list)

class TimelineEvent(BaseModel):
    time: str
    evidences: List[TimelineEvidenceItem]

class TimelineDateItem(BaseModel):
    date: str
    events: List[TimelineEvent]

class TimelinePrototypeOutput(BaseModel):
    items: List[TimelineDateItem]
    model_version: str
    evidence_results: List[EvidenceProcessingResult] = Field(default_factory=list)