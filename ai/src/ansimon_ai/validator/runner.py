from __future__ import annotations

from typing import Callable, Iterable, List

from ansimon_ai.validator.result import (
    ValidationResult,
    ValidationStatus,
    ValidationMessage,
)

ValidatorReturn = ValidationMessage | ValidationResult | Iterable[ValidationMessage] | None
ValidatorFn = Callable[[dict], ValidatorReturn]

class ValidatorRunner:
    def __init__(self, validators: List[ValidatorFn] | None = None):
        self.validators: List[ValidatorFn] = validators or []

    def add(self, validator: ValidatorFn) -> None:
        self.validators.append(validator)

    def run(self, data: dict) -> ValidationResult:
        messages: List[ValidationMessage] = []
        explicit_statuses: List[ValidationStatus] = []

        for validator in self.validators:
            out = validator(data)
            if out is None:
                continue

            if isinstance(out, ValidationResult):
                explicit_statuses.append(out.status)
                messages.extend(out.messages)
                continue

            if isinstance(out, ValidationMessage):
                messages.append(out)
                continue

            # Iterable[ValidationMessage]
            messages.extend(list(out))

        status = self._decide_status(messages, explicit_statuses)

        return ValidationResult(
            status=status,
            messages=messages,
        )

    @staticmethod
    def _decide_status(
        messages: List[ValidationMessage],
        explicit_statuses: List[ValidationStatus],
    ) -> ValidationStatus:
        if explicit_statuses:
            # Prefer explicit results reported by rules. 'FAIL' dominates.
            if any(s == ValidationStatus.FAIL for s in explicit_statuses):
                return ValidationStatus.FAIL
            if any(s == ValidationStatus.WARN for s in explicit_statuses):
                return ValidationStatus.WARN
            return ValidationStatus.PASS

        if not messages:
            return ValidationStatus.PASS

        if any(m.code.startswith("E_") for m in messages):
            return ValidationStatus.FAIL

        return ValidationStatus.WARN