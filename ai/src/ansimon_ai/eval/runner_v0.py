from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Sequence, Tuple

from ansimon_ai.eval.types_v0 import EvalCaseV0, EvalInputKind, EvalSetV0
from ansimon_ai.eval.validator_adapter_v0 import StructuringValidatorV0
from ansimon_ai.llm.mock import MockLLMClient
from ansimon_ai.requirements.event_io_v0 import run_requirement_service_v0
from ansimon_ai.stt.mock import MockSTT
from ansimon_ai.structuring.anchor.matcher import AnchorMatcher
from ansimon_ai.structuring.from_stt import build_structuring_input_from_stt
from ansimon_ai.structuring.run import run_structuring_pipeline_with_tags
from ansimon_ai.validator.tag_validator_v0 import validate_evidence_tags_v0

EvalCaseStatus = Literal["pass", "warn", "fail"]

@dataclass(frozen=True)
class UsageMetricsV0:
    duration_ms: int
    input_chars: int
    output_chars: Optional[int]
    cache_hit: Optional[bool]
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    estimated_cost: Optional[float] = None

@dataclass(frozen=True)
class EvalCaseResultV0:
    case_id: str
    status: EvalCaseStatus
    reason_codes: List[str]
    summary: Dict[str, Any]
    usage_metrics: UsageMetricsV0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "case_id": self.case_id,
            "status": self.status,
            "reason_codes": list(self.reason_codes),
            "summary": dict(self.summary),
            "usage_metrics": self.usage_metrics.__dict__.copy(),
        }

def load_evalset_v0(path: Path) -> EvalSetV0:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return EvalSetV0.model_validate(payload)

def _json_size_chars(obj: Any) -> int:
    return len(json.dumps(obj, ensure_ascii=False, separators=(",", ":")))

def _subset_contains(*, required: Sequence[str], actual: Sequence[str]) -> bool:
    actual_set = set(actual)
    return all(code in actual_set for code in required)

def _compare_case(
    *,
    case: EvalCaseV0,
    actual_requirement_state: str,
    actual_requirement_reason_codes: List[str],
    actual_policy: str,
    actual_can_create_event: bool,
    actual_caution_tag: Optional[str],
    tag_validation_status: str,
    tag_validation_codes: List[str],
) -> Tuple[bool, List[str]]:
    mismatches: List[str] = []

    if actual_requirement_state != case.expected.requirement_state.state:
        mismatches.append("E_REQ_STATE_MISMATCH")

    if not _subset_contains(
        required=case.expected.requirement_state.reason_codes_contains,
        actual=actual_requirement_reason_codes,
    ):
        mismatches.append("E_REQ_REASON_CODES_MISSING")

    if actual_policy != case.expected.event_io.policy:
        mismatches.append("E_EVENT_POLICY_MISMATCH")

    if case.expected.event_io.can_create_event is not None:
        if actual_can_create_event != case.expected.event_io.can_create_event:
            mismatches.append("E_EVENT_CAN_CREATE_MISMATCH")

    if case.expected.event_io.caution_tag is not None:
        if actual_caution_tag != case.expected.event_io.caution_tag:
            mismatches.append("E_EVENT_CAUTION_TAG_MISMATCH")

    if case.expected.tag_validation is not None:
        if case.expected.tag_validation.status is not None:
            if tag_validation_status != case.expected.tag_validation.status:
                mismatches.append("E_TAG_VALIDATION_STATUS_MISMATCH")

        if not _subset_contains(
            required=case.expected.tag_validation.codes_contains,
            actual=tag_validation_codes,
        ):
            mismatches.append("E_TAG_VALIDATION_CODES_MISSING")

    return (len(mismatches) == 0), mismatches

def run_eval_case_v0(
    *,
    case: EvalCaseV0,
    llm_client=None,
    anchor_matcher: Optional[AnchorMatcher] = None,
    validator=None,
    cache: Optional[object] = None,
) -> EvalCaseResultV0:
    if llm_client is None and case.mock_llm_output_json is not None:
        class _CaseLLM:
            def __init__(self, payload: Dict[str, Any]):
                self._payload = payload

            def generate(self, messages):
                return json.dumps(self._payload, ensure_ascii=False)

        llm_client = _CaseLLM(case.mock_llm_output_json)
    else:
        llm_client = llm_client or MockLLMClient()
    anchor_matcher = anchor_matcher or AnchorMatcher()
    validator = validator or StructuringValidatorV0()

    if case.input.kind == EvalInputKind.TEXT:
        stt = MockSTT()
        stt_result = stt.transcribe(case.input.text or "")
        struct_input = build_structuring_input_from_stt(stt_result)
        input_chars = len(struct_input.full_text)
    else:
        if not case.input.structuring_input:
            raise ValueError("structuring_input is required when kind=structuring_input")
        from ansimon_ai.structuring.types import StructuringInput

        struct_input = StructuringInput.model_validate(case.input.structuring_input)
        input_chars = len(struct_input.full_text)

    t0 = time.perf_counter()
    try:
        result, tags = run_structuring_pipeline_with_tags(
            input=struct_input,
            llm_client=llm_client,
            anchor_matcher=anchor_matcher,
            validator=validator,
            cache=cache,
        )

        tag_validation = validate_evidence_tags_v0(tags=tags)

        req = run_requirement_service_v0(
            evidence=result.output_json,
            tags=tags,
            tag_validation=tag_validation,
        )

        duration_ms = int((time.perf_counter() - t0) * 1000)
        output_chars = _json_size_chars(result.output_json)

        actual_requirement_reason_codes = list(req.requirement_state.reason_codes)
        actual_tag_validation_codes = [m.code for m in req.tag_validation.messages]
        actual_requirement_state = req.requirement_state.state.value

        contract_ok, mismatch_codes = _compare_case(
            case=case,
            actual_requirement_state=actual_requirement_state,
            actual_requirement_reason_codes=actual_requirement_reason_codes,
            actual_policy=req.event_io.policy,
            actual_can_create_event=req.event_io.can_create_event,
            actual_caution_tag=req.event_io.caution_tag,
            tag_validation_status=req.tag_validation.status.value,
            tag_validation_codes=actual_tag_validation_codes,
        )
        if not contract_ok:
            status: EvalCaseStatus = "fail"
        elif req.tag_validation.status.value == "warn":
            status = "warn"
        else:
            status = "pass"

        reason_codes: List[str] = []
        for code in [*mismatch_codes, *actual_requirement_reason_codes, *actual_tag_validation_codes]:
            if code not in reason_codes:
                reason_codes.append(code)

        usage = UsageMetricsV0(
            duration_ms=duration_ms,
            input_chars=input_chars,
            output_chars=output_chars,
            cache_hit=getattr(result, "cache_hit", None),
        )

        summary: Dict[str, Any] = {
            "input": case.input.to_brief_str(),
            "structuring": {
                "cache_hit": result.cache_hit,
                "run_id": result.run_id,
                "anchor_stats": result.anchor_stats.model_dump(),
                "validation": result.validation.model_dump(),
            },
            "tags": [t.model_dump() for t in tags],
            "tag_validation": {
                "status": req.tag_validation.status.value,
                "codes": list(actual_tag_validation_codes),
            },
            "requirement_state": {
                "state": actual_requirement_state,
                "reason_codes": list(actual_requirement_reason_codes),
            },
            "event_io": {
                "policy": req.event_io.policy,
                "can_create_event": req.event_io.can_create_event,
                "caution_tag": req.event_io.caution_tag,
                "required_evidence_top_keys": list(req.event_io.required_evidence_top_keys),
            },
        }

        return EvalCaseResultV0(
            case_id=case.case_id,
            status=status,
            reason_codes=reason_codes,
            summary=summary,
            usage_metrics=usage,
        )

    except Exception as e:
        duration_ms = int((time.perf_counter() - t0) * 1000)
        usage = UsageMetricsV0(
            duration_ms=duration_ms,
            input_chars=input_chars,
            output_chars=None,
            cache_hit=None,
        )
        return EvalCaseResultV0(
            case_id=case.case_id,
            status="fail",
            reason_codes=["E_EXCEPTION", type(e).__name__],
            summary={"error": str(e)},
            usage_metrics=usage,
        )

def run_evalset_v0(
    *,
    evalset: EvalSetV0,
    cache: Optional[object] = None,
) -> List[EvalCaseResultV0]:
    results: List[EvalCaseResultV0] = []
    for case in evalset.cases:
        results.append(
            run_eval_case_v0(
                case=case,
                cache=cache,
            )
        )
    return results