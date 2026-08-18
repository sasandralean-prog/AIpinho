from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.artifacts.artifact_diff_preview import ArtifactDiffPreview
from aipinho.schemas.artifacts.artifact_draft import ArtifactDraftRequest
from aipinho.schemas.artifacts.artifact_lifecycle import ArtifactPreviewStatus
from aipinho.schemas.artifacts.artifact_risk import ArtifactRiskAssessment
from aipinho.schemas.artifacts.artifact_source import ArtifactSource
from aipinho.schemas.artifacts.artifact_target import ArtifactTarget
from aipinho.schemas.artifacts.artifact_trace import ArtifactTraceItem
from aipinho.schemas.artifacts.artifact_validation import ArtifactValidation
from aipinho.schemas.common.base import AIpinhoModel


class ArtifactPreviewRequest(ArtifactDraftRequest):
    draft_id: str | None = None


class ArtifactPreview(AIpinhoModel):
    preview_id: str
    draft_id: str | None = None
    status: ArtifactPreviewStatus
    workspace: str
    target: ArtifactTarget
    source: ArtifactSource
    artifact_type: str = "report"
    title: str = ""
    content_preview: str = ""
    content_hash: str = ""
    validation: ArtifactValidation
    risk: ArtifactRiskAssessment
    diff: ArtifactDiffPreview = Field(default_factory=ArtifactDiffPreview)
    approval_required: bool = True
    approval_id: str | None = None
    approval_status: str | None = None
    write_allowed_now: bool = False
    safe_to_execute: bool = False
    would_write: bool = True
    would_overwrite: bool = False
    created_at: str
    updated_at: str
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    trace: list[ArtifactTraceItem] = Field(default_factory=list)
