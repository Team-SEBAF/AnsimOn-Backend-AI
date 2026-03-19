from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field

Confidence = Literal["high", "medium", "low"]

class EvidenceAnchor(BaseModel):
    modality: Literal["text"]
    start_char: int
    end_char: int

class FieldValue(BaseModel):
    value: Any
    confidence: Confidence
    evidence_span: Optional[str] = None
    evidence_anchor: Optional[EvidenceAnchor] = None

class EvidenceMetadataValue(BaseModel):
    evidence_type: Literal["text"] = "text"
    source: Literal["kakao", "sms", "instagram", "email", "unknown"] = "unknown"
    sources: List[Literal["kakao", "sms", "instagram", "email", "unknown"]] = Field(
        default_factory=lambda: ["unknown"]
    )
    created_at: str = "unknown"

class EvidenceMetadata(FieldValue):
    value: EvidenceMetadataValue

class PartiesValue(BaseModel):
    actor: str = "unknown"
    target: str = "unknown"
    relationship: str = "unknown"

class Document(BaseModel):
    evidence_metadata: EvidenceMetadata
    parties: FieldValue
    period: FieldValue
    frequency: FieldValue
    channel: FieldValue
    locations: FieldValue
    action_types: FieldValue
    refusal_signal: FieldValue
    threat_indicators: FieldValue
    impact_on_victim: FieldValue
    report_or_record: FieldValue