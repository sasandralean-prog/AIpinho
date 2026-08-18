from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


ArtifactLibraryStatus = Literal["requested", "generating", "validating", "ready", "failed", "blocked", "expired", "deleted", "archived"]
ArtifactLibraryType = Literal["zip", "markdown_report", "json_report", "text", "image", "patch", "diff", "rollback", "manifest", "log_sanitized", "project_bundle", "validation_report", "promotion_report", "template_output", "unknown"]
ArtifactOriginType = Literal["chat", "sandbox", "project_factory", "autopilot", "skill", "promotion", "validation", "debugger", "manual", "system"]
ArtifactPreviewMode = Literal["metadata_only", "text", "markdown", "json", "image", "zip_listing", "manifest", "safe_summary"]
ArtifactContextUseMode = Literal["attach_as_context", "summarize_first", "manifest_only", "extract_text_safe", "deny"]


class ArtifactRecordV2(AIpinhoModel):
    artifact_id: str
    filename: str
    display_name: str | None = None
    content_type: str = "application/octet-stream"
    size_bytes: int = 0
    status: ArtifactLibraryStatus = "ready"
    artifact_type: ArtifactLibraryType = "unknown"
    origin_type: ArtifactOriginType = "system"
    origin_id: str | None = None
    session_id: str | None = None
    run_id: str | None = None
    agent_id: str | None = None
    project_id: str | None = None
    project_profile_id: str | None = None
    sandbox_task_id: str | None = None
    sandbox_workspace_id: str | None = None
    skill_execution_id: str | None = None
    skill_pack_id: str | None = None
    skill_pack_execution_id: str | None = None
    autopilot_run_id: str | None = None
    promotion_plan_id: str | None = None
    template_execution_id: str | None = None
    validation_id: str | None = None
    policy_decision_ids: list[str] = Field(default_factory=list)
    tool_invocation_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    storage_path_sanitized: str | None = None
    download_endpoint: str | None = None
    requires_token: bool = True
    preview_available: bool = False
    context_usable: bool = False
    retention_policy: str = "keep_final"
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    expires_at: str | None = None
    error_reason: str | None = None
    warnings: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class ArtifactQuery(AIpinhoModel):
    session_id: str | None = None
    project_id: str | None = None
    sandbox_task_id: str | None = None
    skill_execution_id: str | None = None
    skill_pack_id: str | None = None
    skill_pack_execution_id: str | None = None
    autopilot_run_id: str | None = None
    promotion_plan_id: str | None = None
    template_execution_id: str | None = None
    artifact_type: str | None = None
    status: str | None = None
    origin_type: str | None = None
    created_after: str | None = None
    created_before: str | None = None
    text_query: str | None = None
    limit: int = 100
    offset: int = 0
    sort_by: str = "created_at"
    sort_direction: str = "desc"


class ArtifactSearchResult(AIpinhoModel):
    total: int
    items: list[ArtifactRecordV2] = Field(default_factory=list)
    next_offset: int | None = None
    warnings: list[str] = Field(default_factory=list)


class ArtifactPreviewRequest(AIpinhoModel):
    artifact_id: str
    preview_mode: ArtifactPreviewMode = "metadata_only"
    max_bytes: int | None = None
    sanitize: bool = True
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class ArtifactPreviewResult(AIpinhoModel):
    artifact_id: str
    status: str
    preview_mode: ArtifactPreviewMode
    preview_available: bool
    content_preview: str | None = None
    zip_entries: list[dict[str, Any]] = Field(default_factory=list)
    image_info: dict[str, Any] = Field(default_factory=dict)
    manifest: dict[str, Any] = Field(default_factory=dict)
    redaction_applied: bool = False
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class ArtifactContextUseRequest(AIpinhoModel):
    artifact_id: str
    session_id: str
    requesting_agent_id: str = "aipinho"
    use_mode: ArtifactContextUseMode = "attach_as_context"
    sanitization_required: bool = True
    max_context_bytes: int = 65536
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class ArtifactContextUseResult(AIpinhoModel):
    artifact_id: str
    status: str
    use_mode: ArtifactContextUseMode
    context_preview: str | None = None
    reason_code: str
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class ArtifactBundleRequest(AIpinhoModel):
    bundle_request_id: str = Field(default_factory=lambda: f"artifact_bundle_req_{uuid4().hex}")
    artifact_ids: list[str]
    session_id: str | None = None
    project_id: str | None = None
    bundle_name: str = "artifacts_bundle.zip"
    include_manifests: bool = True
    include_reports: bool = True
    require_validation: bool = True
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class ArtifactBundleResult(AIpinhoModel):
    bundle_artifact: ArtifactRecordV2
    included_artifacts: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ArtifactCleanupPreview(AIpinhoModel):
    cleanup_preview_id: str = Field(default_factory=lambda: f"artifact_cleanup_{uuid4().hex}")
    candidate_artifacts: list[ArtifactRecordV2] = Field(default_factory=list)
    total_size_bytes: int = 0
    preserved_artifacts: list[str] = Field(default_factory=list)
    blocked_deletions: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    requires_confirmation: bool = True
    evidence_refs: list[str] = Field(default_factory=list)
