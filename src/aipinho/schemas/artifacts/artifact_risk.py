from __future__ import annotations

from pydantic import Field

from aipinho.schemas.artifacts.artifact_lifecycle import ArtifactRiskLevel
from aipinho.schemas.artifacts.artifact_trace import ArtifactTraceItem
from aipinho.schemas.common.base import AIpinhoModel


class ArtifactRiskAssessment(AIpinhoModel):
    risk_level: ArtifactRiskLevel = "low"
    score: float = 0.0
    approval_required: bool = True
    preview_allowed: bool = True
    blocked: bool = False
    needs_review: bool = False
    reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[ArtifactTraceItem] = Field(default_factory=list)
