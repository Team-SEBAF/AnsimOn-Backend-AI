from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Literal, Optional

from ansimon_ai.validator.result import ValidationResult as RunnerValidationResult
from ansimon_ai.validator.runner import ValidatorRunner
from ansimon_ai.validator.rules.schema_exists import validate_schema_exists
from ansimon_ai.validator.rules.schema.required_keys import validate_required_top_level_keys
from ansimon_ai.validator.rules.schema.confidence_and_evidence import (
    validate_confidence_and_evidence,
)

StructuringStatus = Literal["PASS", "WARN", "FAIL"]

@dataclass(frozen=True)
class StructuringValidationDict:
    status: StructuringStatus
    error_codes: List[str]
    message: Optional[str]

    def to_dict(self) -> Dict:
        return {
            "status": self.status,
            "error_codes": list(self.error_codes),
            "message": self.message,
        }

class StructuringValidatorV0:
    def __init__(self) -> None:
        self._runner = ValidatorRunner(
            [
                validate_schema_exists,
                validate_required_top_level_keys,
                validate_confidence_and_evidence,
            ]
        )

    @staticmethod
    def _map_status(status_value: str) -> StructuringStatus:
        if status_value == "pass":
            return "PASS"
        if status_value == "warn":
            return "WARN"
        return "FAIL"

    def validate(self, output_json: dict) -> Dict:
        r: RunnerValidationResult = self._runner.run(output_json)
        codes = [m.code for m in r.messages]
        message = None
        if r.messages:
            head = r.messages[0]
            message = f"{head.code}: {head.message}"

        payload = StructuringValidationDict(
            status=self._map_status(r.status.value),
            error_codes=codes,
            message=message,
        )
        return payload.to_dict()