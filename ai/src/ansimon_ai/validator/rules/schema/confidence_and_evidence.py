from ansimon_ai.validator.result import ValidationMessage

ALLOWED_CONFIDENCE = {"high", "medium", "low"}

def _validate_confidence(obj: dict, field_path: str) -> ValidationMessage | None:
    value = obj.get("confidence")
    if value not in ALLOWED_CONFIDENCE:
        return ValidationMessage(
            code="E_INVALID_CONFIDENCE",
            message=f"confidence 값이 유효하지 않습니다: {value}",
            field=f"{field_path}.confidence",
        )
    return None

def _validate_evidence_pair(obj: dict, field_path: str) -> ValidationMessage | None:
    span = obj.get("evidence_span")
    anchor = obj.get("evidence_anchor")

    if span is None:
        if anchor is not None:
            return ValidationMessage(
                code="E_ANCHOR_WITHOUT_SPAN",
                message="evidence_span이 null인데 evidence_anchor가 존재합니다.",
                field=f"{field_path}.evidence_anchor",
            )
        return None

    if anchor is None:
        return None

    if anchor.get("modality") != "text":
        return ValidationMessage(
            code="E_INVALID_ANCHOR_MODALITY",
            message="evidence_anchor.modality는 'text'여야 합니다.",
            field=f"{field_path}.evidence_anchor.modality",
        )

    start = anchor.get("start_char")
    end = anchor.get("end_char")

    if not isinstance(start, int) or not isinstance(end, int) or start >= end:
        return ValidationMessage(
            code="E_INVALID_ANCHOR_RANGE",
            message="evidence_anchor의 start_char/end_char 범위가 유효하지 않습니다.",
            field=f"{field_path}.evidence_anchor",
        )

    return None

def validate_confidence_and_evidence(data: dict) -> ValidationMessage | None:
    for key, obj in data.items():
        if not isinstance(obj, dict):
            continue

        msg = _validate_confidence(obj, key)
        if msg:
            return msg

        msg = _validate_evidence_pair(obj, key)
        if msg:
            return msg

    return None