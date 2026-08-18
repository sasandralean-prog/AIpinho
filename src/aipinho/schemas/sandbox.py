from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


SandboxWorkspaceRole = Literal["sandbox_mutable", "sandbox_readonly", "sandbox_artifact", "sandbox_tmp", "sandbox_import"]
SandboxTaskStatus = Literal["created", "running", "completed", "cancelled", "blocked", "failed"]
SandboxOperationStatus = Literal["allowed", "blocked", "succeeded", "ready", "failed", "preview"]


class SandboxWorkspace(AIpinhoModel):
    sandbox_workspace_id: str = Field(default_factory=lambda: f"sandbox_ws_{uuid4().hex}")
    name: str
    display_name: str | None = None
    role: SandboxWorkspaceRole = "sandbox_mutable"
    status: str = "active"
    root_path_sanitized: str
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    owner_agent_id: str | None = None
    session_id: str | None = None
    task_id: str | None = None
    allowed_operations: list[str] = Field(default_factory=list)
    limits: dict[str, Any] = Field(default_factory=dict)
    policy_profile_id: str = "sandbox_default"
    evidence_refs: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class SandboxTask(AIpinhoModel):
    sandbox_task_id: str = Field(default_factory=lambda: f"sandbox_task_{uuid4().hex}")
    sandbox_workspace_id: str
    title: str
    slug: str = "sandbox_task"
    user_goal: str = ""
    session_id: str | None = None
    agent_id: str | None = None
    workspace_id: str | None = None
    task_root_sanitized: str | None = None
    status: SandboxTaskStatus = "created"
    created_by_agent_id: str | None = None
    created_files: list[str] = Field(default_factory=list)
    modified_files: list[str] = Field(default_factory=list)
    deleted_files: list[str] = Field(default_factory=list)
    shell_command_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    validation_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class SandboxPolicyDecision(AIpinhoModel):
    allowed: bool
    reason_code: str
    human_reason: str
    risk_level: str = "low"
    safe_alternative: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class SandboxPathResolution(AIpinhoModel):
    sandbox_workspace_id: str
    relative_path: str
    absolute_path_sanitized: str
    within_sandbox: bool
    exists: bool = False
    is_symlink: bool = False
    policy_decision: SandboxPolicyDecision


class SandboxFileOperation(AIpinhoModel):
    operation_id: str = Field(default_factory=lambda: f"sandbox_fileop_{uuid4().hex}")
    sandbox_task_id: str | None = None
    sandbox_workspace_id: str
    operation_type: str
    relative_path: str | None = None
    absolute_path_sanitized: str | None = None
    status: SandboxOperationStatus
    reason_code: str
    bytes_written: int = 0
    bytes_read: int = 0
    hash: str | None = None
    before_hash: str | None = None
    after_hash: str | None = None
    policy_decision_id: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class SandboxShellCommand(AIpinhoModel):
    command_id: str = Field(default_factory=lambda: f"sandbox_shell_{uuid4().hex}")
    sandbox_task_id: str | None = None
    sandbox_workspace_id: str
    command: str
    command_sanitized: str | None = None
    normalized_command: list[str] = Field(default_factory=list)
    cwd_relative: str = "."
    category: str = "unknown_shell"
    status: SandboxOperationStatus
    reason_code: str
    exit_code: int | None = None
    stdout_sanitized: str = ""
    stderr_sanitized: str = ""
    duration_ms: int = 0
    timeout_seconds: int = 120
    policy_decision_id: str | None = None
    validation_id: str | None = None
    stdout_ref: str | None = None
    stderr_ref: str | None = None
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)


class SandboxArtifactExport(AIpinhoModel):
    artifact_export_id: str = Field(default_factory=lambda: f"sandbox_export_{uuid4().hex}")
    sandbox_task_id: str | None = None
    sandbox_workspace_id: str
    project_generation_id: str | None = None
    source_directory_sanitized: str | None = None
    artifact_id: str | None = None
    filename: str
    content_type: str = "application/zip"
    size: int = 0
    status: SandboxOperationStatus
    reason_code: str
    download_endpoint: str | None = None
    requires_token: bool = True
    manifest_path: str | None = None
    validation_id: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class SandboxValidationResult(AIpinhoModel):
    validation_id: str = Field(default_factory=lambda: f"sandbox_validation_{uuid4().hex}")
    sandbox_task_id: str | None = None
    validation_type: str = "sandbox_contract"
    status: str
    checks: list[dict[str, Any]] = Field(default_factory=list)
    checked_files: list[str] = Field(default_factory=list)
    checked_artifacts: list[str] = Field(default_factory=list)
    command_refs: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)


class SandboxStatus(AIpinhoModel):
    status: str
    root_path_sanitized: str
    workspaces: int
    tasks: int
    artifacts: int
    policy_version: str
    warnings: list[str] = Field(default_factory=list)


class SandboxFileRequest(AIpinhoModel):
    sandbox_workspace_id: str
    sandbox_task_id: str | None = None
    relative_path: str
    content: str | None = None
    expected_hash: str | None = None
    destination_relative_path: str | None = None
    overwrite: bool = False
    max_bytes: int = 1_000_000


class SandboxShellRequest(AIpinhoModel):
    sandbox_workspace_id: str
    sandbox_task_id: str | None = None
    command: str
    cwd_relative: str = "."
    timeout_seconds: int = 120
    category: str | None = None


class SandboxArtifactExportRequest(AIpinhoModel):
    sandbox_workspace_id: str
    sandbox_task_id: str | None = None
    project_generation_id: str | None = None
    filename: str = "sandbox_artifact.zip"
    include_paths: list[str] = Field(default_factory=lambda: ["."])
    exclude_globs: list[str] = Field(default_factory=list)


class SandboxCleanupPreviewRequest(AIpinhoModel):
    sandbox_workspace_id: str | None = None
    max_age_hours: int = 24
    include_tmp: bool = True
    include_trash: bool = True


class SandboxCleanupPreview(AIpinhoModel):
    cleanup_preview_id: str = Field(default_factory=lambda: f"sandbox_cleanup_{uuid4().hex}")
    candidates: list[dict[str, Any]] = Field(default_factory=list)
    status: str = "preview"
    reason_code: str = "sandbox_cleanup_preview_allowed"
    created_at: str = Field(default_factory=utc_now_iso)
