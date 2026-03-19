from typing import Dict, Iterable
from ansimon_ai.validator.result import ValidationMessage

def validate_anchor_consistency(data: Dict) -> Iterable[ValidationMessage]:
    messages: list[ValidationMessage] = []

    for field, obj in data.items():
        if not isinstance(obj, dict):
            continue

        evidence_span = obj.get("evidence_span")
        evidence_anchor = obj.get("evidence_anchor")

        if evidence_span is None and evidence_anchor is not None:
            messages.append(
                ValidationMessage(
                    code="E_ANCHOR_WITHOUT_SPAN",
                    field=field,
                    message="evidence_anchor must be null when evidence_span is null",
                )
            )
            continue

        if evidence_anchor is not None:
            start = evidence_anchor.get("start_char")
            end = evidence_anchor.get("end_char")

            if not isinstance(start, int) or not isinstance(end, int):
                messages.append(
                    ValidationMessage(
                        code="E_ANCHOR_INVALID_RANGE",
                        field=field,
                        message="evidence_anchor.start_char and end_char must be integers",
                    )
                )
                continue

            if start >= end:
                messages.append(
                    ValidationMessage(
                        code="E_ANCHOR_INVALID_RANGE",
                        field=field,
                        message="evidence_anchor.start_char must be less than end_char",
                    )
                )

    return messages