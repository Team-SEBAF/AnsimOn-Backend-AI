from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel


# AI INPUT
class IncidentLogFormInput(BaseModel):
    title: str
    date: str
    time: str
    place: str
    situation: str


class TimelinePrototypeEvidenceInput(BaseModel):
    evidence_id: UUID
    type: Literal["MESSAGE", "VOICE", "VICTIM", "REPORT_RECORD", "INCIDENT_LOG"]
    file_format: Optional[Literal["IMAGE", "AUDIO", "VIDEO", "PDF", "HWP", "DOCX", "TXT"]] = None
    file_name: Optional[str] = None
    file_bytes: Optional[bytes] = None
    extracted_text: Optional[str] = None
    incident_log_form: Optional[IncidentLogFormInput] = None


class TimelinePrototypeAiInput(BaseModel):
    complaint_id: UUID
    evidences: list[TimelinePrototypeEvidenceInput]


# AI OUTPUT
class EvidenceProcessingResult(BaseModel):
    evidence_id: UUID
    type: Literal["MESSAGE", "VOICE", "VICTIM", "REPORT_RECORD", "INCIDENT_LOG"]
    status: Literal["completed", "skipped", "failed"]
    source_type: Optional[Literal["ocr", "stt", "document", "form"]] = None
    normalized_text: Optional[str] = None
    structured_data: Optional[dict] = None
    timestamp: Optional[datetime] = None
    title: Optional[str] = None
    description: Optional[str] = None
    tags: list[Literal["repeat", "physical", "threat", "sexual_insult", "refusal"]] = []
    error_code: Optional[str] = None
    error_message: Optional[str] = None


class TimelineEvidenceItem(BaseModel):
    timeline_evidence_id: UUID
    index: int
    title: str
    description: str
    tags: list[Literal["repeat", "physical", "threat", "sexual_insult", "refusal"]] = []
    referenced_evidence_count: int = 1
    referenced_evidence_ids: list[UUID] = []


class TimelineEvent(BaseModel):
    time: str
    evidences: list[TimelineEvidenceItem]


class TimelineDateItem(BaseModel):
    date: str
    events: list[TimelineEvent]


class TimelinePrototypeOutput(BaseModel):
    items: list[TimelineDateItem]
    model_version: str
    evidence_results: list[EvidenceProcessingResult]
