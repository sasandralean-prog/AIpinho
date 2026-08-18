from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchRiskAssessment(AIpinhoModel):
    risk_level: str = "medium"
    preview_allowed: bool = True
    needs_review: bool = True
    blocked: bool = False
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
