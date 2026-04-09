from typing import Dict, List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field

TagType = Literal[
    "repeat",
    "physical",
    "threat",
    "sexual_insult",
    "refusal",
]

class ComplaintWritingTimelineItem(BaseModel):
    title: str
    description: Optional[str] = None
    tags: List[TagType] = Field(default_factory=list)
    is_ai_original: bool
    referenced_evidence_ids: List[UUID] = Field(default_factory=list)

class ComplaintWritingEvent(BaseModel):
    time: str
    evidences: List[ComplaintWritingTimelineItem]

class ComplaintWritingDateItem(BaseModel):
    date: str
    events: List[ComplaintWritingEvent]

class ComplaintWritingStructuredContext(BaseModel):
    evidence_id: UUID
    parties: Optional[Dict[str, str]] = None
    period: Optional[str] = None
    frequency: Optional[str] = None
    channel: List[str] = Field(default_factory=list)
    locations: List[str] = Field(default_factory=list)
    action_types: List[str] = Field(default_factory=list)
    refusal_signal: Optional[str] = None
    threat_indicators: List[str] = Field(default_factory=list)
    impact_on_victim: List[str] = Field(default_factory=list)
    report_or_record: Optional[str] = None

class ComplaintWritingAiInput(BaseModel):
    complaint_id: UUID
    items: List[ComplaintWritingDateItem]
    structured_contexts: List[ComplaintWritingStructuredContext] = Field(
        default_factory=list
    )

class ComplaintDocumentOutput(BaseModel):
    section_4_crime_facts: str
    section_5_complaint_reason: str
    section_6_evidence_list_text: List[str]

class DamageFactsStatementOutput(BaseModel):
    damage_facts_statement: str