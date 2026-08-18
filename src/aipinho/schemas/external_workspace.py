from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.projects.project_profile import ProjectProfileCandidate


ExternalWorkspaceRole = Literal["source_readonly", "target_mutable", "sandbox_import", "protected", "forbidden"]
ExternalWorkspaceStatus = Literal["candidate", "registered", "blocked", "import_preview", "imported", "failed"]


class ExternalPathCandidate(AIpinhoModel):
    candidate_id: str = Field(default_factory=lambda: f"external_path_{uuid4().hex}")
    raw_path: str
    resolved_path: str
    exists: bool
    is_directory: bool
    is_file: bool
    role_hint: ExternalWorkspaceRole | None = None
    status: ExternalWorkspaceStatus = "candidate"
    reason_code: str = "external_path_detected"
    confidence: float = 0.8
    safe_actions: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class WorkspaceRegistrationRequest(AIpinhoModel):
    path: str
    role: ExternalWorkspaceRole
    display_name: str | None = None
    reason: str | None = None
    allow_missing: bool = False
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class WorkspaceRegistrationResult(AIpinhoModel):
    workspace_id: str = Field(default_factory=lambda: f"external_ws_{uuid4().hex}")
    path: str
    role: ExternalWorkspaceRole
    display_name: str | None = None
    status: ExternalWorkspaceStatus = "registered"
    allowed_operations: list[str] = Field(default_factory=list)
    blocked_operations: list[str] = Field(default_factory=list)
    reason_code: str = "workspace_registered"
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    project_profile_candidate: ProjectProfileCandidate | None = None
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class WorkspaceOnboardingRequest(AIpinhoModel):
    prompt: str | None = None
    path: str | None = None
    requested_action: str = "detect"
    role: ExternalWorkspaceRole | None = None
    display_name: str | None = None
    import_target_name: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class WorkspaceImportRequest(AIpinhoModel):
    source_workspace_id: str | None = None
    source_path: str | None = None
    target_name: str | None = None
    include_globs: list[str] = Field(default_factory=lambda: ["**/*"])
    exclude_globs: list[str] = Field(default_factory=list)
    max_files: int | None = None
    max_bytes: int | None = None
    dry_run: bool = True
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class WorkspaceImportPlan(AIpinhoModel):
    import_plan_id: str = Field(default_factory=lambda: f"workspace_import_plan_{uuid4().hex}")
    source_path: str
    target_name: str
    target_sandbox_workspace_id: str | None = None
    status: str = "preview"
    files_total: int = 0
    files_included: int = 0
    files_excluded: int = 0
    bytes_total: int = 0
    included_files: list[dict[str, Any]] = Field(default_factory=list)
    excluded_files: list[dict[str, Any]] = Field(default_factory=list)
    secret_findings: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    policy_decision: dict[str, Any] = Field(default_factory=dict)
    project_profile_candidate: ProjectProfileCandidate | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)


class WorkspaceBridgeManifest(AIpinhoModel):
    bridge_manifest_id: str = Field(default_factory=lambda: f"workspace_bridge_{uuid4().hex}")
    source_workspace_id: str | None = None
    source_path: str
    sandbox_workspace_id: str
    sandbox_root_path: str
    role: ExternalWorkspaceRole = "sandbox_import"
    files: list[dict[str, Any]] = Field(default_factory=list)
    secret_findings: list[dict[str, Any]] = Field(default_factory=list)
    project_profile_candidate_id: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)


class WorkspaceImportResult(AIpinhoModel):
    import_result_id: str = Field(default_factory=lambda: f"workspace_import_{uuid4().hex}")
    import_plan_id: str
    status: str
    source_path: str
    sandbox_workspace_id: str | None = None
    sandbox_root_path: str | None = None
    manifest: WorkspaceBridgeManifest | None = None
    files_copied: int = 0
    bytes_copied: int = 0
    artifact_id: str | None = None
    download_endpoint: str | None = None
    requires_token: bool = True
    validation_status: str = "unknown"
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)


class WorkspaceOnboardingResult(AIpinhoModel):
    status: str
    requested_action: str
    candidates: list[ExternalPathCandidate] = Field(default_factory=list)
    registration: WorkspaceRegistrationResult | None = None
    import_plan: WorkspaceImportPlan | None = None
    import_result: WorkspaceImportResult | None = None
    message: str
    safe_actions: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
