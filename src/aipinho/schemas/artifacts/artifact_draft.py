from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.artifacts.artifact_lifecycle import ArtifactDraftStatus
from aipinho.schemas.artifacts.artifact_source import ArtifactSource
from aipinho.schemas.artifacts.artifact_trace import ArtifactTraceItem
from aipinho.schemas.common.base import AIpinhoModel


class ArtifactDraftRequest(AIpinhoModel):
    workspace: str
    target_path: str
    source: ArtifactSource = Field(default_factory=ArtifactSource)
    artifact_type: str = "report"
    title: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactDraft(AIpinhoModel):
    draft_id: str
    status: ArtifactDraftStatus = "draft"
    workspace: str
    target_path: str
    source: ArtifactSource
    artifact_type: str = "report"
    title: str = ""
    created_at: str
    updated_at: str
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    trace: list[ArtifactTraceItem] = Field(default_factory=list)
