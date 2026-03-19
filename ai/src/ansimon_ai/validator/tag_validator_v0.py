from __future__ import annotations
from typing import List, Sequence

from ansimon_ai.structuring.tags.types import EvidenceTag
from ansimon_ai.validator.result import (
    ValidationMessage,
    ValidationResult,
    ValidationStatus,
)

def validate_evidence_tags_v0(*, tags: Sequence[EvidenceTag]) -> ValidationResult:
    if not tags:
        return ValidationResult(
            status=ValidationStatus.WARN,
            messages=[
                ValidationMessage(
                    code="W_NO_TAGS",
                    field=None,
                    message="no evidence tags provided",
                )
            ],
        )

    tag_values = {t.tag for t in tags}
    messages: List[ValidationMessage] = []

    if "STRUCT_INVALID" in tag_values:
        struct_tag = next((t for t in tags if t.tag == "STRUCT_INVALID"), None)
        detail = f" ({struct_tag.note})" if struct_tag and struct_tag.note else ""

        messages.append(
            ValidationMessage(
                code="E_STRUCT_INVALID",
                field="structure",
                message=f"structured output is invalid{detail}",
            )
        )

        return ValidationResult(
            status=ValidationStatus.FAIL,
            messages=messages,
        )

    if "ANCHOR_AMBIGUOUS" in tag_values:
        anchor_tag = next((t for t in tags if t.tag == "ANCHOR_AMBIGUOUS"), None)
        detail = f" ({anchor_tag.note})" if anchor_tag and anchor_tag.note else ""

        messages.append(
            ValidationMessage(
                code="W_ANCHOR_AMBIGUOUS",
                field="anchor",
                message=f"anchor match is ambiguous{detail}",
            )
        )
    elif "ANCHOR_NOT_FOUND" in tag_values:
        anchor_tag = next((t for t in tags if t.tag == "ANCHOR_NOT_FOUND"), None)
        detail = f" ({anchor_tag.note})" if anchor_tag and anchor_tag.note else ""

        messages.append(
            ValidationMessage(
                code="W_ANCHOR_NOT_FOUND",
                field="anchor",
                message=f"no reproducible anchor match{detail}",
            )
        )

    if "CONFIDENCE_WITHOUT_ANCHOR" in tag_values:
        messages.append(
            ValidationMessage(
                code="W_CONFIDENCE_WITHOUT_ANCHOR",
                field="confidence",
                message="confidence is present without reproducible anchor",
            )
        )

    if not ("STRUCT_VALID" in tag_values or "STRUCT_INVALID" in tag_values):
        messages.append(
            ValidationMessage(
                code="W_TAGS_INCOMPLETE",
                field=None,
                message="structure validity tag is missing",
            )
        )

    status = ValidationStatus.PASS if not messages else ValidationStatus.WARN

    return ValidationResult(
        status=status,
        messages=messages,
    )