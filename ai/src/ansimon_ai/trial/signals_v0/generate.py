from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence

from ansimon_ai.structuring.tags.types import EvidenceTag
from ansimon_ai.structuring.types import StructuringResult
from ansimon_ai.trial.signals_v0.types import (
    TrialSignalEvidenceV0,
    TrialSignalV0,
    TrialSignalsOutputV0,
)
from ansimon_ai.validator.result import ValidationStatus
from ansimon_ai.validator.tag_validator_v0 import validate_evidence_tags_v0

DEFAULT_FULL_TEXT_MAX_CHARS = 1000
DEFAULT_EVIDENCE_SPAN_MAX_CHARS = 240
DEFAULT_SUMMARY_MAX_CHARS = 80
DEFAULT_REASON_CODES_MAX_ITEMS = 8

W_INPUT_TRUNCATED = "W_INPUT_TRUNCATED"
W_EVIDENCE_TRUNCATED = "W_EVIDENCE_TRUNCATED"
W_OUTPUT_TRUNCATED = "W_OUTPUT_TRUNCATED"

@dataclass(frozen=True)
class _SpanMatch:
    span: str
    start: int
    end: int

def _find_first_match(full_text: str, patterns: Iterable[str]) -> Optional[_SpanMatch]:
    for pat in patterns:
        m = re.search(pat, full_text, flags=re.IGNORECASE | re.MULTILINE)
        if not m:
            continue

        start, end = m.start(), m.end()
        span = full_text[start:end]
        if span:
            return _SpanMatch(span=span, start=start, end=end)

    return None

def _make_text_evidence(*, full_text: str, match: _SpanMatch) -> TrialSignalEvidenceV0:
    return TrialSignalEvidenceV0(
        evidence_span=match.span,
        evidence_anchor={
            "modality": "text",
            "start_char": match.start,
            "end_char": match.end,
        },
        source="text",
        source_field=None,
    )

def _truncate_text(*, text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars <= 0:
        return "", bool(text)

    if len(text) <= max_chars:
        return text, False

    return text[:max_chars], True

def _truncate_evidence(*, ev: TrialSignalEvidenceV0, max_chars: int) -> tuple[TrialSignalEvidenceV0, bool]:
    if max_chars <= 0:
        if not ev.evidence_span:
            return ev, False

        return (
            TrialSignalEvidenceV0(
                evidence_span="",
                evidence_anchor=ev.evidence_anchor,
                source=ev.source,
                source_field=ev.source_field,
            ),
            True,
        )

    if len(ev.evidence_span) <= max_chars:
        return ev, False

    new_span = ev.evidence_span[:max_chars]

    new_anchor = ev.evidence_anchor
    if new_anchor is not None:
        if isinstance(new_anchor, dict):
            start = new_anchor.get("start_char")
            end = new_anchor.get("end_char")
            if isinstance(start, int) and isinstance(end, int):
                new_end = min(end, start + len(new_span))
                new_anchor = {**new_anchor, "end_char": new_end}
        else:
            start = getattr(new_anchor, "start_char", None)
            end = getattr(new_anchor, "end_char", None)
            modality = getattr(new_anchor, "modality", None)
            if isinstance(start, int) and isinstance(end, int) and isinstance(modality, str):
                new_end = min(end, start + len(new_span))
                new_anchor = {
                    "modality": modality,
                    "start_char": start,
                    "end_char": new_end,
                }

    return (
        TrialSignalEvidenceV0(
            evidence_span=new_span,
            evidence_anchor=new_anchor,
            source=ev.source,
            source_field=ev.source_field,
        ),
        True,
    )

def _cap_reason_codes(*, codes: List[str], max_items: int) -> tuple[List[str], bool]:
    if max_items <= 0:
        return [], bool(codes)

    if len(codes) <= max_items:
        return codes, False

    kept = codes[: max_items - 1]
    kept.append(W_OUTPUT_TRUNCATED)
    return kept, True

def _cap_summary(*, summary: str, max_chars: int) -> tuple[str, bool]:
    return _truncate_text(text=summary, max_chars=max_chars)

def _repetition_level(full_text: str) -> tuple[str, List[str], List[TrialSignalEvidenceV0]]:
    tokens = [t.strip() for t in re.split(r"\s+", full_text) if t.strip()]
    freq: dict[str, int] = {}

    for t in tokens:
        if len(t) < 4:
            continue
        freq[t] = freq.get(t, 0) + 1

    if not freq:
        return "부족", ["T_REPETITION_NO_TOKENS"], []

    token, count = max(freq.items(), key=lambda kv: kv[1])

    if count >= 3:
        match = _find_first_match(full_text, [re.escape(token)])
        ev = [_make_text_evidence(full_text=full_text, match=match)] if match else []
        return "충분", ["T_REPETITION_TOKEN_X3"], ev

    if count == 2:
        match = _find_first_match(full_text, [re.escape(token)])
        ev = [_make_text_evidence(full_text=full_text, match=match)] if match else []
        return "경고", ["T_REPETITION_TOKEN_X2"], ev

    return "부족", ["T_REPETITION_TOKEN_X1"], []

_THREAT_PATTERNS = [
    r"죽(?:여|인다|이겠)",
    r"가만두지\s*않",
    r"해코지",
    r"찾아가(?:겠|서)",
    r"때리(?:겠|고)",
    r"폭로",
]

def _threat_level(full_text: str) -> tuple[str, List[str], List[TrialSignalEvidenceV0]]:
    match = _find_first_match(full_text, _THREAT_PATTERNS)
    if not match:
        return "부족", ["T_THREAT_NO_MATCH"], []

    return "충분", ["T_THREAT_KEYWORD_MATCH"], [_make_text_evidence(full_text=full_text, match=match)]

_REFUSAL_PATTERNS = [
    r"그만",
    r"하지\s*마",
    r"싫어",
    r"연락\s*하지\s*마",
    r"차단",
    r"거절",
]

def _refusal_level(full_text: str) -> tuple[str, List[str], List[TrialSignalEvidenceV0]]:
    match = _find_first_match(full_text, _REFUSAL_PATTERNS)
    if not match:
        return "부족", ["T_REFUSAL_NO_MATCH"], []

    return "충분", ["T_REFUSAL_KEYWORD_MATCH"], [_make_text_evidence(full_text=full_text, match=match)]

def generate_trial_signals_v0_from_text(
    *,
    full_text: str,
    full_text_max_chars: int = DEFAULT_FULL_TEXT_MAX_CHARS,
    evidence_span_max_chars: int = DEFAULT_EVIDENCE_SPAN_MAX_CHARS,
    summary_max_chars: int = DEFAULT_SUMMARY_MAX_CHARS,
    reason_codes_max_items: int = DEFAULT_REASON_CODES_MAX_ITEMS,
) -> TrialSignalsOutputV0:
    full_text, input_truncated = _truncate_text(text=full_text, max_chars=full_text_max_chars)

    rep_level, rep_codes, rep_ev = _repetition_level(full_text)
    thr_level, thr_codes, thr_ev = _threat_level(full_text)
    ref_level, ref_codes, ref_ev = _refusal_level(full_text)

    if input_truncated:
        rep_codes = rep_codes + [W_INPUT_TRUNCATED]
        thr_codes = thr_codes + [W_INPUT_TRUNCATED]
        ref_codes = ref_codes + [W_INPUT_TRUNCATED]

    rep_ev2: List[TrialSignalEvidenceV0] = []
    rep_ev_trunc = False
    for ev in rep_ev:
        ev2, trunc = _truncate_evidence(ev=ev, max_chars=evidence_span_max_chars)
        rep_ev2.append(ev2)
        rep_ev_trunc = rep_ev_trunc or trunc

    thr_ev2: List[TrialSignalEvidenceV0] = []
    thr_ev_trunc = False
    for ev in thr_ev:
        ev2, trunc = _truncate_evidence(ev=ev, max_chars=evidence_span_max_chars)
        thr_ev2.append(ev2)
        thr_ev_trunc = thr_ev_trunc or trunc

    ref_ev2: List[TrialSignalEvidenceV0] = []
    ref_ev_trunc = False
    for ev in ref_ev:
        ev2, trunc = _truncate_evidence(ev=ev, max_chars=evidence_span_max_chars)
        ref_ev2.append(ev2)
        ref_ev_trunc = ref_ev_trunc or trunc

    if rep_ev_trunc:
        rep_codes = rep_codes + [W_EVIDENCE_TRUNCATED]
    if thr_ev_trunc:
        thr_codes = thr_codes + [W_EVIDENCE_TRUNCATED]
    if ref_ev_trunc:
        ref_codes = ref_codes + [W_EVIDENCE_TRUNCATED]

    rep_codes, _ = _cap_reason_codes(codes=rep_codes, max_items=reason_codes_max_items)
    thr_codes, _ = _cap_reason_codes(codes=thr_codes, max_items=reason_codes_max_items)
    ref_codes, _ = _cap_reason_codes(codes=ref_codes, max_items=reason_codes_max_items)

    summary, _ = _cap_summary(summary="TRIAL signals v0 (text)", max_chars=summary_max_chars)

    return TrialSignalsOutputV0(
        mode="text",
        version="v0",
        summary=summary,
        signals=[
            TrialSignalV0(name="repetition", level=rep_level, reason_codes=rep_codes, evidence=rep_ev2),
            TrialSignalV0(name="threat", level=thr_level, reason_codes=thr_codes, evidence=thr_ev2),
            TrialSignalV0(name="refusal", level=ref_level, reason_codes=ref_codes, evidence=ref_ev2),
        ],
    )

def _extract_structured_evidence_pool(
    *,
    result: StructuringResult,
    max_evidence: int,
) -> List[TrialSignalEvidenceV0]:
    pool: List[TrialSignalEvidenceV0] = []

    if not isinstance(result.output_json, dict):
        return pool

    for field, obj in result.output_json.items():
        if not isinstance(obj, dict):
            continue

        span = obj.get("evidence_span")
        anchor = obj.get("evidence_anchor")

        if span is None:
            continue

        pool.append(
            TrialSignalEvidenceV0(
                evidence_span=span,
                evidence_anchor=anchor,
                source="structuring",
                source_field=field,
            )
        )

        if len(pool) >= max_evidence:
            break

    return pool

def generate_trial_signals_v0_from_structuring(
    *,
    result: StructuringResult,
    tags: Sequence[EvidenceTag],
    max_evidence: int = 3,
    evidence_span_max_chars: int = DEFAULT_EVIDENCE_SPAN_MAX_CHARS,
    summary_max_chars: int = DEFAULT_SUMMARY_MAX_CHARS,
    reason_codes_max_items: int = DEFAULT_REASON_CODES_MAX_ITEMS,
) -> TrialSignalsOutputV0:
    tag_validation = validate_evidence_tags_v0(tags=tags)
    tag_values = {t.tag for t in tags}

    evidence_pool0 = _extract_structured_evidence_pool(result=result, max_evidence=max_evidence)
    evidence_pool: List[TrialSignalEvidenceV0] = []
    evidence_truncated = False
    for ev in evidence_pool0:
        ev2, trunc = _truncate_evidence(ev=ev, max_chars=evidence_span_max_chars)
        evidence_pool.append(ev2)
        evidence_truncated = evidence_truncated or trunc

    conf_values: List[str] = []
    if isinstance(result.output_json, dict):
        for ev in evidence_pool:
            if not ev.source_field:
                continue
            obj = result.output_json.get(ev.source_field)
            if isinstance(obj, dict):
                conf = obj.get("confidence")
                if isinstance(conf, str):
                    conf_values.append(conf)

    if not evidence_pool:
        strength_level = "위험"
        strength_codes = ["E_NO_EVIDENCE_POOL"]
    elif any(c == "low" for c in conf_values):
        strength_level = "위험"
        strength_codes = ["E_CONFIDENCE_LOW_PRESENT"]
    elif any(c == "medium" for c in conf_values):
        strength_level = "경고"
        strength_codes = ["E_CONFIDENCE_MEDIUM_PRESENT"]
    else:
        strength_level = "안전"
        strength_codes = ["E_CONFIDENCE_HIGH_ONLY"]

    if "STRUCT_INVALID" in tag_values:
        clarity_level = "위험"
        clarity_codes = ["E_STRUCT_INVALID"]
    elif "ANCHOR_OK" in tag_values:
        clarity_level = "안전"
        clarity_codes = ["E_ANCHOR_OK"]
    elif "ANCHOR_AMBIGUOUS" in tag_values:
        clarity_level = "경고"
        clarity_codes = ["W_ANCHOR_AMBIGUOUS"]
    elif "ANCHOR_NOT_FOUND" in tag_values:
        clarity_level = "경고"
        clarity_codes = ["W_ANCHOR_NOT_FOUND"]
    else:
        clarity_level = "경고"
        clarity_codes = ["W_ANCHOR_STATE_UNKNOWN"]

    if tag_validation.status == ValidationStatus.FAIL:
        safety_level = "위험"
        safety_codes = ["E_TAG_VALIDATION_FAIL"] + [m.code for m in tag_validation.messages]
    elif tag_validation.status == ValidationStatus.WARN:
        safety_level = "경고"
        safety_codes = ["W_TAG_VALIDATION_WARN"] + [m.code for m in tag_validation.messages]
    else:
        safety_level = "안전"
        safety_codes = ["P_TAG_VALIDATION_PASS"]

    if evidence_truncated:
        strength_codes = strength_codes + [W_EVIDENCE_TRUNCATED]
        clarity_codes = clarity_codes + [W_EVIDENCE_TRUNCATED]
        safety_codes = safety_codes + [W_EVIDENCE_TRUNCATED]

    strength_codes, _ = _cap_reason_codes(codes=strength_codes, max_items=reason_codes_max_items)
    clarity_codes, _ = _cap_reason_codes(codes=clarity_codes, max_items=reason_codes_max_items)
    safety_codes, _ = _cap_reason_codes(codes=safety_codes, max_items=reason_codes_max_items)

    summary, _ = _cap_summary(summary="TRIAL signals v0 (evidence)", max_chars=summary_max_chars)

    return TrialSignalsOutputV0(
        mode="evidence",
        version="v0",
        summary=summary,
        signals=[
            TrialSignalV0(
                name="evidence_strength",
                level=strength_level,
                reason_codes=strength_codes,
                evidence=evidence_pool,
            ),
            TrialSignalV0(
                name="clarity",
                level=clarity_level,
                reason_codes=clarity_codes,
                evidence=evidence_pool,
            ),
            TrialSignalV0(
                name="safety",
                level=safety_level,
                reason_codes=safety_codes,
                evidence=evidence_pool,
            ),
        ],
    )