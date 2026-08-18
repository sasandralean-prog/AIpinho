from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.validation.validation_finding import ValidationFinding
from aipinho.schemas.validation.validation_trace import ValidationTraceItem

class ValidationGateResult(AIpinhoModel):
    validation_id: str
    target_type: str
    target_id: str | None = None
    status: str
    score: float
    safe_to_display: bool = True
    deterministic_only: bool = True
    findings: list[ValidationFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocking_findings: list[str] = Field(default_factory=list)
    trace: list[ValidationTraceItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def summary(self) -> dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "status": self.status,
            "score": self.score,
            "safe_to_display": self.safe_to_display,
            "warnings": list(self.warnings),
            "blocking_findings": list(self.blocking_findings),
        }
