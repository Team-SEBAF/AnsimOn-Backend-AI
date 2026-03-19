from typing import Dict, Any

from ansimon_ai.validator.result import (
    ValidationMessage,
    ValidationResult,
    ValidationStatus,
)

ALLOWED_CONFIDENCE = {"high", "medium", "low"}

def validate_confidence_value(payload: Dict[str, Any]) -> ValidationResult:
    messages: list[ValidationMessage] = []

    for field_name, field_obj in payload.items():
        if not isinstance(field_obj, dict):
            continue

        confidence = field_obj.get("confidence")
        evidence_span = field_obj.get("evidence_span")

        if confidence is None:
            messages.append(
                ValidationMessage(
                    code="confidence_missing",
                    field=field_name,
                    message="confidence field is missing",
                )
            )
            continue

        if confidence not in ALLOWED_CONFIDENCE:
            messages.append(
                ValidationMessage(
                    code="confidence_invalid_value",
                    field=field_name,
                    message=f"invalid confidence value: {confidence}",
                )
            )
            continue

        if confidence == "high" and evidence_span is None:
            messages.append(
                ValidationMessage(
                    code="confidence_high_requires_evidence",
                    field=field_name,
                    message="confidence=high requires evidence_span",
                )
            )

    if messages:
        return ValidationResult(
            status=ValidationStatus.FAIL,
            messages=messages,
        )

    return ValidationResult(
        status=ValidationStatus.PASS,
        messages=[],
    )