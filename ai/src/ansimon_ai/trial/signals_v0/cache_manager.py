from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from ansimon_ai.structuring.cache.hash import compute_input_hash
from ansimon_ai.structuring.types import StructuringInput, StructuringResult
from ansimon_ai.structuring.tags.types import EvidenceTag
from ansimon_ai.trial.signals_v0.generate import generate_trial_signals_v0_from_structuring
from ansimon_ai.trial.signals_v0.storage import load_json, save_json
from ansimon_ai.trial.signals_v0.types import TrialSignalsOutputV0

def _default_storage_path(*, trial_version: str, input_hash: str, filename: str) -> Path:
    return Path("data") / "trial_signals" / trial_version / input_hash / filename

def _trial_limits_tag(
    *,
    full_text_max_chars: int,
    evidence_span_max_chars: int,
    summary_max_chars: int,
    reason_codes_max_items: int,
) -> str:
    return (
        f"ft{full_text_max_chars}"
        f"_es{evidence_span_max_chars}"
        f"_s{summary_max_chars}"
        f"_rc{reason_codes_max_items}"
    )

def _parse_trial_output(payload: dict) -> TrialSignalsOutputV0:
    result = payload.get("result")
    if not isinstance(result, dict):
        raise ValueError("invalid cache payload: missing result")

    if hasattr(TrialSignalsOutputV0, "model_validate"):
        return TrialSignalsOutputV0.model_validate(result)

    return TrialSignalsOutputV0.parse_obj(result)

def get_or_create_trial_signals_v0_from_structuring(
    *,
    struct_input: StructuringInput,
    result: StructuringResult,
    tags: list[EvidenceTag],
    schema_version: str = "v1.3",
    prompt_version: str = "v1.0",
    trial_version: str = "v0",
    max_evidence: int = 3,
    full_text_max_chars: int = 1000,
    evidence_span_max_chars: int = 240,
    summary_max_chars: int = 80,
    reason_codes_max_items: int = 8,
    storage_path_fn: Callable[[str, str, str], Path] | None = None,
) -> TrialSignalsOutputV0:
    input_hash = compute_input_hash(
        struct_input,
        schema_version=schema_version,
        prompt_version=prompt_version,
    )

    limits_tag = _trial_limits_tag(
        full_text_max_chars=full_text_max_chars,
        evidence_span_max_chars=evidence_span_max_chars,
        summary_max_chars=summary_max_chars,
        reason_codes_max_items=reason_codes_max_items,
    )

    filename = f"signals__mode_evidence__m{max_evidence}__{limits_tag}.json"
    path_fn = storage_path_fn or (lambda tv, ih, fn: _default_storage_path(trial_version=tv, input_hash=ih, filename=fn))
    path = path_fn(trial_version, input_hash, filename)

    cached = load_json(path)
    if cached is not None:
        return _parse_trial_output(cached)

    trial = generate_trial_signals_v0_from_structuring(
        result=result,
        tags=tags,
        max_evidence=max_evidence,
        evidence_span_max_chars=evidence_span_max_chars,
        summary_max_chars=summary_max_chars,
        reason_codes_max_items=reason_codes_max_items,
    )

    payload = {
        "_metadata": {
            "schema_version": schema_version,
            "prompt_version": prompt_version,
            "trial_version": trial_version,
            "mode": "evidence",
            "input_hash": input_hash,
            "max_evidence": max_evidence,
            "limits": {
                "full_text_max_chars": full_text_max_chars,
                "evidence_span_max_chars": evidence_span_max_chars,
                "summary_max_chars": summary_max_chars,
                "reason_codes_max_items": reason_codes_max_items,
            },
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "result": trial.model_dump() if hasattr(trial, "model_dump") else trial.dict(),
    }

    save_json(path, payload)
    return trial