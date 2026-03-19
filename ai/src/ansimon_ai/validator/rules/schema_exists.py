from ansimon_ai.validator.result import ValidationMessage

def validate_schema_exists(data: dict) -> ValidationMessage | None:
    if not isinstance(data, dict):
        return ValidationMessage(
            code="E_NOT_OBJECT",
            message="출력 결과가 JSON 객체가 아닙니다.",
            field=None,
        )
    return None
