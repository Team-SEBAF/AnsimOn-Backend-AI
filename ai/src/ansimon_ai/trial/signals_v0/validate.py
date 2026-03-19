from __future__ import annotations
import re
from typing import Iterable

from ansimon_ai.trial.signals_v0.types import TrialSignalsOutputV0
from ansimon_ai.validator.result import (
    ValidationMessage,
    ValidationResult,
    ValidationStatus,
)

_TEXT_NAMES = {"repetition", "threat", "refusal"}
_EVIDENCE_NAMES = {"evidence_strength", "clarity", "safety"}

_TEXT_LEVELS = {"부족", "경고", "충분"}
_EVIDENCE_LEVELS = {"위험", "경고", "안전"}

_REASON_CODE_RE = re.compile(r"^[TEWP]_[A-Z0-9_]+$")

def _iter_signal_names(output: TrialSignalsOutputV0) -> Iterable[str]:
    for s in output.signals:
        yield s.name

def validate_trial_signals_output_v0(*, output: TrialSignalsOutputV0) -> ValidationResult:
    messages: list[ValidationMessage] = []

    if output.version != "v0":
        messages.append(
            ValidationMessage(
                code="E_VERSION",
                field="version",
                message=f"unexpected version: {output.version}",
            )
        )

    if output.mode == "text":
        names = list(_iter_signal_names(output))
        if set(names) != _TEXT_NAMES:
            messages.append(
                ValidationMessage(
                    code="E_SIGNAL_SET",
                    field="signals",
                    message="text mode must contain exactly repetition/threat/refusal",
                )
            )

        for s in output.signals:
            if not s.reason_codes:
                messages.append(
                    ValidationMessage(
                        code="E_REASON_CODES_EMPTY",
                        field=f"signals[{s.name}].reason_codes",
                        message="reason_codes must be non-empty",
                    )
                )
            else:
                for rc in s.reason_codes:
                    if not isinstance(rc, str) or not _REASON_CODE_RE.match(rc):
                        messages.append(
                            ValidationMessage(
                                code="W_REASON_CODE_FORMAT",
                                field=f"signals[{s.name}].reason_codes",
                                message=f"reason_code must match ^[TEWP]_[A-Z0-9_]+$: {rc!r}",
                            )
                        )

            if s.level not in _TEXT_LEVELS:
                messages.append(
                    ValidationMessage(
                        code="E_LEVEL",
                        field=f"signals[{s.name}].level",
                        message=f"invalid text level: {s.level}",
                    )
                )

    elif output.mode == "evidence":
        names = list(_iter_signal_names(output))
        if set(names) != _EVIDENCE_NAMES:
            messages.append(
                ValidationMessage(
                    code="E_SIGNAL_SET",
                    field="signals",
                    message="evidence mode must contain exactly evidence_strength/clarity/safety",
                )
            )

        for s in output.signals:
            if not s.reason_codes:
                messages.append(
                    ValidationMessage(
                        code="E_REASON_CODES_EMPTY",
                        field=f"signals[{s.name}].reason_codes",
                        message="reason_codes must be non-empty",
                    )
                )
            else:
                for rc in s.reason_codes:
                    if not isinstance(rc, str) or not _REASON_CODE_RE.match(rc):
                        messages.append(
                            ValidationMessage(
                                code="W_REASON_CODE_FORMAT",
                                field=f"signals[{s.name}].reason_codes",
                                message=f"reason_code must match ^[TEWP]_[A-Z0-9_]+$: {rc!r}",
                            )
                        )

            if s.level not in _EVIDENCE_LEVELS:
                messages.append(
                    ValidationMessage(
                        code="E_LEVEL",
                        field=f"signals[{s.name}].level",
                        message=f"invalid evidence level: {s.level}",
                    )
                )

            if len(s.evidence) > 3:
                messages.append(
                    ValidationMessage(
                        code="E_MAX_EVIDENCE",
                        field=f"signals[{s.name}].evidence",
                        message="evidence list must be <= 3",
                    )
                )

    else:
        messages.append(
            ValidationMessage(
                code="E_MODE",
                field="mode",
                message=f"unexpected mode: {output.mode}",
            )
        )

    status = ValidationStatus.PASS if not messages else ValidationStatus.WARN
    return ValidationResult(status=status, messages=messages)