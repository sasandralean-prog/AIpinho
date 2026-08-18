from __future__ import annotations

from pydantic import Field

from aipinho.schemas.artifacts.artifact_content import ArtifactContentValidation
from aipinho.schemas.artifacts.artifact_target import ArtifactTargetValidation
from aipinho.schemas.common.base import AIpinhoModel


class ArtifactValidation(AIpinhoModel):
    valid: bool = False
    target: ArtifactTargetValidation
    content: ArtifactContentValidation
    validation_gate_summary: dict[str, object] = Field(default_factory=dict)
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
