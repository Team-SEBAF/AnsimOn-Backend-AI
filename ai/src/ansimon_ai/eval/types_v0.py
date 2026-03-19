from __future__ import annotations
from enum import Enum
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

class EvalInputKind(str, Enum):
    TEXT = "text"
    STRUCTURING_INPUT = "structuring_input"

class EvalInputV0(BaseModel):
    kind: EvalInputKind
    text: Optional[str] = None
    structuring_input: Optional[Dict[str, Any]] = None

    def to_brief_str(self) -> str:
        if self.kind == EvalInputKind.TEXT:
            return f"text({len(self.text or '')} chars)"
        return "structuring_input"

class ExpectedRequirementStateV0(BaseModel):
    state: Literal["EVALUATABLE", "UNSTABLE", "INVALID"]
    reason_codes_contains: List[str] = Field(default_factory=list)

class ExpectedEventIOV0(BaseModel):
    policy: Literal["deny", "allow", "allow_with_caution"]
    can_create_event: Optional[bool] = None
    caution_tag: Optional[Literal["UNSTABLE"]] = None

class ExpectedTagValidationV0(BaseModel):
    status: Optional[Literal["pass", "warn", "fail"]] = None
    codes_contains: List[str] = Field(default_factory=list)

class EvalExpectedV0(BaseModel):
    requirement_state: ExpectedRequirementStateV0
    event_io: ExpectedEventIOV0
    tag_validation: Optional[ExpectedTagValidationV0] = None

class EvalCaseV0(BaseModel):
    case_id: str
    input: EvalInputV0
    expected: EvalExpectedV0
    mock_llm_output_json: Optional[Dict[str, Any]] = None

class EvalSetV0(BaseModel):
    version: Literal["evalset_v0"]
    name: str
    cases: List[EvalCaseV0]