from __future__ import annotations

from typing import Literal

from aipinho.schemas.common.base import AIpinhoModel

EvaluationSeverity = Literal["low", "medium", "high", "critical"]


class EvaluationFinding(AIpinhoModel):
    code: str
    severity: EvaluationSeverity = "medium"
    message: str
    source: str = "evaluation"
    critical: bool = False
    evidence_id: str | None = None
