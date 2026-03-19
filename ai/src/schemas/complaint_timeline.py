from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel

class EvidenceRequest(BaseModel):
    id: UUID
    type: Literal[
        "MESSAGE",
        "VOICE",
        "VICTIM",
        "REPORT_RECORD",
        "INCIDENT_LOG",
    ]

class TimelineRequest(BaseModel):
    evidences: List[EvidenceRequest]

TagType = Literal[
    "repeat",
    "physical",
    "threat",
    "sexual_insult",
    "refusal",
]

class TimelineEvidence(BaseModel):
    timeline_evidence_id: UUID
    index: int
    title: str
    description: str
    tags: List[TagType]
    referenced_evidence_count: int
    referenced_evidence_ids: List[UUID]

class TimelineEvent(BaseModel):
    time: str
    evidences: List[TimelineEvidence]

class TimelineDateItem(BaseModel):
    date: str
    events: List[TimelineEvent]

class TimelineResponse(BaseModel):
    items: List[TimelineDateItem]
    model_version: Optional[str] = None