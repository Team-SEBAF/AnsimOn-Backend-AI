from ansimon_ai.validator.result import ValidationError

REQUIRED_TOP_KEYS = [
    "evidence_metadata", "parties", "period", "frequency", "channel",
    "locations", "action_types", "refusal_signal",
    "threat_indicators", "impact_on_victim", "report_or_record",
]

COMMON_FIELDS = ["value", "confidence", "evidence_span", "evidence_anchor"]
CONFIDENCE_VALUES = {"high", "medium", "low"}

def validate_required_keys(doc: dict) -> list[ValidationError]:
    errors: list[ValidationError] = []

    for k in REQUIRED_TOP_KEYS:
        if k not in doc:
            errors.append(ValidationError("MISSING_REQUIRED_KEY", k))

    for k in REQUIRED_TOP_KEYS:
        field = doc.get(k)
        if not isinstance(field, dict):
            continue

        for cf in COMMON_FIELDS:
            if cf not in field:
                errors.append(ValidationError("MISSING_COMMON_FIELD", f"{k}.{cf}"))

        conf = field.get("confidence")
        if conf is not None and conf not in CONFIDENCE_VALUES:
            errors.append(ValidationError("INVALID_CONFIDENCE", f"{k}.confidence"))

        span = field.get("evidence_span")
        anchor = field.get("evidence_anchor")
        if (span is None) != (anchor is None):
            errors.append(ValidationError("SPAN_ANCHOR_INCONSISTENT", k))

    return errors