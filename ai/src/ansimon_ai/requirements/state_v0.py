from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional, Sequence

from ansimon_ai.structuring.tags.types import EvidenceTag
from ansimon_ai.validator.result import ValidationResult, ValidationStatus
from ansimon_ai.validator.tag_validator_v0 import validate_evidence_tags_v0

class RequirementState(str, Enum):
    EVALUATABLE = "EVALUATABLE"
    UNSTABLE = "UNSTABLE"
    INVALID = "INVALID"

@dataclass(frozen=True)
class RequirementStateResult:
    state: RequirementState
    reason_codes: List[str]

def evaluate_requirement_state_v0(
    *,
    tags: Sequence[EvidenceTag],
    tag_validation: Optional[ValidationResult] = None,
) -> RequirementStateResult:
    if tag_validation is None:
        tag_validation = validate_evidence_tags_v0(tags=tags)

    codes = [m.code for m in tag_validation.messages]

    if tag_validation.status == ValidationStatus.FAIL:
        return RequirementStateResult(state=RequirementState.INVALID, reason_codes=codes)

    if tag_validation.status == ValidationStatus.WARN:
        return RequirementStateResult(state=RequirementState.UNSTABLE, reason_codes=codes)

    return RequirementStateResult(state=RequirementState.EVALUATABLE, reason_codes=codes)