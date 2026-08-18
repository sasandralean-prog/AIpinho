from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


ToolInvocationStatus = Literal[
    "created",
    "policy_checking",
    "approval_required",
    "auto_approved",
    "running",
    "succeeded",
    "succeeded_with_warnings",
    "blocked",
    "failed",
    "cancelled",
]

PolicyDecisionValue = Literal["allow", "deny", "require_approval", "auto_approve"]
WorkspaceRole = Literal["source_readonly", "target_mutable", "system_mutable", "protected", "forbidden", "unknown"]
ToolArtifactStatus = Literal["requested", "generating", "validating", "ready", "failed", "blocked", "expired", "deleted"]


class ToolDefinition(AIpinhoModel):
    tool_name: str
    display_name: str
    description: str
    capability: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "low"
    requires_workspace: bool = False
    requires_policy_check: bool = True
    requires_approval: bool = False
    supports_autoapproval: bool = True
    emits_events: bool = True
    produces_artifacts: bool = False
    can_modify_filesystem: bool = False
    can_run_shell: bool = False
    enabled: bool = True
    agent_allowlist: list[str] = Field(default_factory=list)
    agent_denylist: list[str] = Field(default_factory=list)


class ToolRegistryStatus(AIpinhoModel):
    status: str
    tools_loaded: int
    enabled_tools: int
    disabled_tools: int
    tool_names: list[str] = Field(default_factory=list)


class WorkspaceResolution(AIpinhoModel):
    workspace_id: str | None = None
    workspace_role: WorkspaceRole = "unknown"
    root_path_sanitized: str | None = None
    resolved_path_sanitized: str | None = None
    allowed: bool = False
    reason_code: str = "workspace_unknown"
    evidence_refs: list[str] = Field(default_factory=list)


class PolicyDecision(AIpinhoModel):
    policy_decision_id: str = Field(default_factory=lambda: f"policy_decision_{uuid4().hex}")
    agent_id: str | None = None
    session_id: str | None = None
    run_id: str | None = None
    tool_invocation_id: str | None = None
    operation_type: str | None = None
    capability: str | None = None
    workspace_id: str | None = None
    workspace_role: WorkspaceRole | None = None
    risk_level: str = "low"
    execution_mode: str = "governed_autorun"
    decision: PolicyDecisionValue
    reason_code: str
    human_reason: str
    technical_reason_sanitized: str
    approval_required: bool = False
    auto_approval_id: str | None = None
    safe_alternative: str | None = None
    safe_actions: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)


class ValidationStep(AIpinhoModel):
    step_id: str = Field(default_factory=lambda: f"validation_step_{uuid4().hex}")
    name: str
    status: str
    evidence_refs: list[str] = Field(default_factory=list)
    human_message: str
    technical_summary_sanitized: str | None = None


class ValidationResult(AIpinhoModel):
    validation_id: str = Field(default_factory=lambda: f"validation_{uuid4().hex}")
    status: str
    steps: list[ValidationStep] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)


class ToolArtifactRecord(AIpinhoModel):
    artifact_id: str = Field(default_factory=lambda: f"agent_artifact_{uuid4().hex}")
    session_id: str
    run_id: str | None = None
    parent_run_id: str | None = None
    delegation_id: str | None = None
    agent_id: str
    tool_invocation_id: str | None = None
    project_profile_id: str | None = None
    filename: str
    content_type: str = "application/octet-stream"
    size: int = 0
    size_bytes: int = 0
    status: ToolArtifactStatus = "ready"
    origin: str = "agent_generated"
    requires_token: bool = True
    download_endpoint: str | None = None
    validation_id: str | None = None
    sandbox_task_id: str | None = None
    project_generation_id: str | None = None
    error_reason: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class ToolInvocationCreateRequest(AIpinhoModel):
    operation_type: str | None = None
    workspace_id: str | None = None
    project_profile_id: str | None = None
    workspace_profile_id: str | None = None
    validation_profile_id: str | None = None
    command_profile_id: str | None = None
    skill_id: str | None = None
    skill_execution_id: str | None = None
    sandbox_task_id: str | None = None
    sandbox_workspace_id: str | None = None
    relative_path: str | None = None
    cwd_inside_sandbox: str | None = None
    operation_scope: str | None = None
    requesting_agent_id: str | None = None
    path_ref: str | None = None
    input: dict[str, Any] = Field(default_factory=dict)
    approval_id: str | None = None
    auto_approval_id: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class ToolInvocation(AIpinhoModel):
    tool_invocation_id: str = Field(default_factory=lambda: f"tool_invocation_{uuid4().hex}")
    run_id: str
    parent_run_id: str | None = None
    delegation_id: str | None = None
    session_id: str
    agent_id: str
    tool_name: str
    capability: str
    operation_type: str
    workspace_id: str | None = None
    project_profile_id: str | None = None
    workspace_profile_id: str | None = None
    validation_profile_id: str | None = None
    command_profile_id: str | None = None
    skill_id: str | None = None
    skill_execution_id: str | None = None
    sandbox_task_id: str | None = None
    sandbox_workspace_id: str | None = None
    relative_path: str | None = None
    cwd_inside_sandbox: str | None = None
    operation_scope: str | None = None
    requesting_agent_id: str | None = None
    workspace_role: WorkspaceRole | None = None
    input_summary_sanitized: str
    input_ref: str | None = None
    policy_decision_id: str | None = None
    approval_id: str | None = None
    auto_approval_id: str | None = None
    status: ToolInvocationStatus = "created"
    started_at: str = Field(default_factory=utc_now_iso)
    completed_at: str | None = None
    output_summary_sanitized: str | None = None
    output_ref: str | None = None
    artifact_ids: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    error_code: str | None = None
    block_reason_code: str | None = None
    raw_ref: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class ToolInvocationResult(AIpinhoModel):
    status: str
    tool_invocation: ToolInvocation
    policy_decision: PolicyDecision | None = None
    workspace_resolution: WorkspaceResolution | None = None
    output: dict[str, Any] = Field(default_factory=dict)
    validation_result: ValidationResult | None = None
    artifacts: list[ToolArtifactRecord] = Field(default_factory=list)
    events_emitted: list[str] = Field(default_factory=list)
    raw_hidden_by_default: bool = True


class ArtifactUploadRequest(AIpinhoModel):
    filename: str
    content_type: str = "application/octet-stream"
    content: str
    encoding: str = "text"
    run_id: str | None = None
    project_profile_id: str | None = None
    origin: str = "agent_generated"
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)
