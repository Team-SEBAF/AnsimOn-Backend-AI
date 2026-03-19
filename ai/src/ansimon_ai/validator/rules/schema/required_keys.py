from ansimon_ai.validator.result import ValidationMessage

REQUIRED_TOP_LEVEL_KEYS = [
    "evidence_metadata",
    "parties",
    "period",
    "frequency",
    "channel",
    "locations",
    "action_types",
    "refusal_signal",
    "threat_indicators",
    "impact_on_victim",
    "report_or_record",
]

def validate_required_top_level_keys(data: dict) -> ValidationMessage | None:
    missing_keys = [
        key for key in REQUIRED_TOP_LEVEL_KEYS if key not in data
    ]

    if missing_keys:
        return ValidationMessage(
            code="E_REQUIRED_KEY_MISSING",
            message=f"필수 최상위 키가 누락되었습니다: {', '.join(missing_keys)}",
            field=".",
        )

    return None