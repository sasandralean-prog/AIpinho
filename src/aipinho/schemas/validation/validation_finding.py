from __future__ import annotations
from typing import Literal
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

ValidationStatus = Literal["passed", "passed_with_warnings", "failed", "rejected", "needs_review", "degraded"]
ValidationSeverity = Literal["info", "warning", "error", "critical"]

class ValidationFinding(AIpinhoModel):
    finding_id: str
    code: str
    title: str
    severity: ValidationSeverity = "warning"
    message: str
    evidence: list[str] = Field(default_factory=list)
    validator: str = "unknown"
    blocking: bool = False
    safe_to_display: bool = True
