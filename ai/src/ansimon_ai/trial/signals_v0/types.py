from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel

from ansimon_ai.validator.schema import EvidenceAnchor

TrialSignalsVersion = Literal["v0"]
TrialSignalsMode = Literal["text", "evidence"]

TextSignalName = Literal["repetition", "threat", "refusal"]
EvidenceSignalName = Literal["evidence_strength", "clarity", "safety"]
TrialSignalName = TextSignalName | EvidenceSignalName

TextSignalLevel = Literal["부족", "경고", "충분"]
EvidenceSignalLevel = Literal["위험", "경고", "안전"]
TrialSignalLevel = TextSignalLevel | EvidenceSignalLevel

class TrialSignalEvidenceV0(BaseModel):
    evidence_span: str
    evidence_anchor: Optional[EvidenceAnchor] = None
    source: Literal["text", "structuring"]
    source_field: Optional[str] = None

class TrialSignalV0(BaseModel):
    name: TrialSignalName
    level: TrialSignalLevel
    reason_codes: List[str]
    evidence: List[TrialSignalEvidenceV0]

class TrialSignalsOutputV0(BaseModel):
    mode: TrialSignalsMode
    version: TrialSignalsVersion
    summary: str
    signals: List[TrialSignalV0]