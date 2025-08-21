from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ValidationIssue:
    code: str
    message: str
    path: Optional[str] = None

@dataclass
class ValidationReport:
    ok: bool
    checked: int = 0
    errors: List[ValidationIssue] = field(default_factory=list)

    def fail(self, code: str, message: str, path: Optional[str] = None):
        self.ok = False
        self.errors.append(ValidationIssue(code, message, path))
