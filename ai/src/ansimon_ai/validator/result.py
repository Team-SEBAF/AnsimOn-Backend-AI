from enum import Enum
from dataclasses import dataclass
from typing import List, Optional

@dataclass(frozen=True)
class ValidationError:
    code: str
    field: str
    message: Optional[str] = None

class ValidationStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"

@dataclass
class ValidationMessage:
    code: str
    message: str
    field: Optional[str] = None

@dataclass
class ValidationResult:
    status: ValidationStatus
    messages: List[ValidationMessage]

    @property
    def is_valid(self) -> bool:
        return self.status != ValidationStatus.FAIL