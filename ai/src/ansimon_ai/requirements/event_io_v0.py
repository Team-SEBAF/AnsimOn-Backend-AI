from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, Sequence

from ansimon_ai.requirements.state_v0 import (
    RequirementState,
    RequirementStateResult,
    evaluate_requirement_state_v0,
)
from ansimon_ai.structuring.tags.types import EvidenceTag
from ansimon_ai.validator.tag_validator_v0 import validate_evidence_tags_v0
from ansimon_ai.validator.result import ValidationResult

EvidenceV13 = Dict[str, Any]

DEFAULT_REQUIRED_EVIDENCE_TOP_KEYS_V0: List[str] = [
    "evidence_metadata",
    "parties",
    "period",
    "frequency",
    "channel",
    "locations",
    "action_types",
    "refusal_signal",
    "threat_indicators",
    "impact_on_victim",
    "report_or_record",
]

@dataclass(frozen=True)
class RequirementRuleEngineInputV0:
    evidence: EvidenceV13
    tags: Sequence[EvidenceTag]
    tag_validation: ValidationResult
    requirement_state: RequirementStateResult

@dataclass(frozen=True)
class RequirementRuleEngineOutputV0:
    can_create_event: bool
    policy: Literal["deny", "allow", "allow_with_caution"]
    reason_codes: List[str]
    required_evidence_top_keys: List[str]
    caution_tag: Optional[Literal["UNSTABLE"]] = None

@dataclass(frozen=True)
class RequirementServiceResultV0:
    tag_validation: ValidationResult
    requirement_state: RequirementStateResult
    event_io: RequirementRuleEngineOutputV0

def evaluate_event_io_contract_v0(
    *,
    requirement_state: RequirementStateResult,
    required_evidence_top_keys: Optional[List[str]] = None,
) -> RequirementRuleEngineOutputV0:
    keys = (
        list(DEFAULT_REQUIRED_EVIDENCE_TOP_KEYS_V0)
        if required_evidence_top_keys is None
        else list(required_evidence_top_keys)
    )

    if requirement_state.state == RequirementState.INVALID:
        return RequirementRuleEngineOutputV0(
            can_create_event=False,
            policy="deny",
            reason_codes=list(requirement_state.reason_codes),
            required_evidence_top_keys=keys,
            caution_tag=None,
        )

    if requirement_state.state == RequirementState.UNSTABLE:
        return RequirementRuleEngineOutputV0(
            can_create_event=True,
            policy="allow_with_caution",
            reason_codes=list(requirement_state.reason_codes),
            required_evidence_top_keys=keys,
            caution_tag="UNSTABLE",
        )

    return RequirementRuleEngineOutputV0(
        can_create_event=True,
        policy="allow",
        reason_codes=list(requirement_state.reason_codes),
        required_evidence_top_keys=keys,
        caution_tag=None,
    )

def run_requirement_service_v0(
    *,
    evidence: EvidenceV13,
    tags: Sequence[EvidenceTag],
    tag_validation: Optional[ValidationResult] = None,
    requirement_state: Optional[RequirementStateResult] = None,
    required_evidence_top_keys: Optional[List[str]] = None,
) -> RequirementServiceResultV0:
    if tag_validation is None:
        tag_validation = validate_evidence_tags_v0(tags=tags)

    if requirement_state is None:
        requirement_state = evaluate_requirement_state_v0(
            tags=tags,
            tag_validation=tag_validation,
        )

    event_io = evaluate_event_io_contract_v0(
        requirement_state=requirement_state,
        required_evidence_top_keys=required_evidence_top_keys,
    )

    return RequirementServiceResultV0(
        tag_validation=tag_validation,
        requirement_state=requirement_state,
        event_io=event_io,
    )