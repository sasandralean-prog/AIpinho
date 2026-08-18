from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.artifacts.artifact_lifecycle import ArtifactFormat, ArtifactSourceType
from aipinho.schemas.common.base import AIpinhoModel


class ArtifactSource(AIpinhoModel):
    source_type: ArtifactSourceType = "user_provided_content"
    source_id: str | None = None
    format: ArtifactFormat = "markdown"
    content: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactResolvedSource(AIpinhoModel):
    source: ArtifactSource
    content: str
    format: ArtifactFormat = "markdown"
    status: str = "resolved"
    validation_summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
