from __future__ import annotations

from typing import Literal

from aipinho.schemas.common.base import AIpinhoModel

SafetySeverity = Literal["low", "medium", "high", "critical"]


class SafetyViolation(AIpinhoModel):
    violation_id: str
    type: str
    severity: SafetySeverity = "critical"
    message: str
    critical: bool = True
    redacted_excerpt: str | None = None
