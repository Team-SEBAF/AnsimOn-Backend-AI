from typing import Optional
from ansimon_ai.structuring.types import (
    StructuringInput,
    StructuringResult,
    AnchorStats,
    ValidationResult,
)
from ansimon_ai.structuring.anchor.matcher import AnchorMatcher
from ansimon_ai.structuring.cache.hash import compute_input_hash
from ansimon_ai.structuring.call import call_structuring_ai
from ansimon_ai.structuring.anchor.apply import apply_anchors
from ansimon_ai.structuring.anchor.store import collect_anchors, save_anchors
from ansimon_ai.structuring.tags.generate import generate_evidence_tags
from ansimon_ai.structuring.tags.types import EvidenceTag
from ansimon_ai.trial.signals_v0.cache_manager import get_or_create_trial_signals_v0_from_structuring

SCHEMA_VERSION = "v1.3"
PROMPT_VERSION = "v1.0"

def run_structuring_pipeline(
        *,
        input: StructuringInput,
        llm_client,
        anchor_matcher: AnchorMatcher,
        validator,
        cache: Optional[object] = None,
) -> StructuringResult:
    # 1. cache check
    cache_hit = False
    cached_output = None
    cache_key = None

    if cache is not None:
        cache_key = compute_input_hash(
            input,
            schema_version=SCHEMA_VERSION,
            prompt_version=PROMPT_VERSION,
        )
        cached_output = cache.get(cache_key)

        if cached_output is not None:
            cache_hit = True

    # 2. LLM call (구조화)
    if cached_output is None:
        output_json = call_structuring_ai(
            struct_input=input,
            llm_client=llm_client,
        )

        if cache is not None and cache_key is not None:
            cache.set(cache_key, output_json)
    else:
        output_json = cached_output
    
    # 3. anchor matching & apply
    anchored_json = apply_anchors(
        structuring_result=output_json,
        full_text=input.full_text,
        matcher=anchor_matcher,
    )

    anchors = collect_anchors(structuring_result=anchored_json)

    total_spans = len(anchors)
    matched = 0
    unmatched = 0

    for item in anchors:
        if item["evidence_anchor"] is None:
            unmatched += 1
        else:
            matched += 1

    anchor_stats = AnchorStats(
        total_spans=total_spans,
        matched_spans=matched,
        partial_matched_spans=0,
        unmatched_spans=unmatched,
        notes=None,
    )

    # 4. anchor store (분리 저장)
    if cache_key is not None:
        save_anchors(
            anchors=anchors,
            schema_version=SCHEMA_VERSION,
            input_hash=cache_key,
        )

    # 5. validation
    raw_validation = validator.validate(anchored_json)

    validation_result = ValidationResult(
        status=raw_validation.get("status", "FAIL"),
        error_codes=raw_validation.get("error_codes", []),
        message=raw_validation.get("message"),
    )

    # 6. collect result
    result = StructuringResult(
        output_json=anchored_json,
        cache_hit=cache_hit,
        anchor_stats=anchor_stats,
        validation=validation_result,
        run_id=cache_key,
    )

    return result

def run_structuring_pipeline_with_tags(
        *,
        input: StructuringInput,
        llm_client,
        anchor_matcher: AnchorMatcher,
        validator,
        cache: Optional[object] = None,
) -> tuple[StructuringResult, list[EvidenceTag]]:
    result = run_structuring_pipeline(
        input=input,
        llm_client=llm_client,
        anchor_matcher=anchor_matcher,
        validator=validator,
        cache=cache,
    )

    evidence_tags = generate_evidence_tags(result=result)
    return result, evidence_tags

def run_structuring_pipeline_with_tags_and_trial_signals_v0(
        *,
        input: StructuringInput,
        llm_client,
        anchor_matcher: AnchorMatcher,
        validator,
        cache: Optional[object] = None,
        max_trial_evidence: int = 3,
):
    result, evidence_tags = run_structuring_pipeline_with_tags(
        input=input,
        llm_client=llm_client,
        anchor_matcher=anchor_matcher,
        validator=validator,
        cache=cache,
    )

    trial = get_or_create_trial_signals_v0_from_structuring(
        struct_input=input,
        result=result,
        tags=evidence_tags,
        schema_version=SCHEMA_VERSION,
        prompt_version=PROMPT_VERSION,
        max_evidence=max_trial_evidence,
    )

    return result, evidence_tags, trial