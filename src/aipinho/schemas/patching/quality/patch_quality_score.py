from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchQualityScore(AIpinhoModel):
    status: str = "unknown"
    score: float = 0.0
    max_score: float = 100.0
    blocking_findings: int = 0
    warning_count: int = 0
    critical_count: int = 0
    decision_reason: str = ""
    dimensions: dict[str, float] = Field(default_factory=dict)
