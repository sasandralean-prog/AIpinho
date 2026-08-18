from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


DelegationStatus = Literal[
    "created",
    "policy_checking",
    "accepted",
    "approval_required",
    "rejected",
    "running",
    "completed",
    "completed_with_warnings",
    "blocked",
    "failed",
    "cancelled",
    "timed_out",
]

DelegationDecision = Literal["allow", "deny", "require_approval", "auto_approve"]


class DelegationCreateRequest(AIpinhoModel):
    target_agent_id: str
    target_session_id: str | None = None
    user_goal: str
    requested_operation: str
    operation_type: str | None = None
    workspace_id: str | None = None
    project_profile_id: str | None = None
    workspace_profile_id: str | None = None
    validation_profile_id: str | None = None
    command_profile_ids: list[str] = Field(default_factory=list)
    project_context_summary_sanitized: dict[str, Any] = Field(default_factory=dict)
    skill_id: str | None = None
    skill_version: str | None = None
    skill_inputs: dict[str, Any] = Field(default_factory=dict)
    expected_skill_outputs: list[str] = Field(default_factory=list)
    capabilities_requested: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: list[str] = Field(default_factory=list)
    memory_refs: list[str] = Field(default_factory=list)
    memory_context_sanitized: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "low"
    execution_mode: str | None = None
    autoapproval_policy: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int | None = None
    max_child_steps: int | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class DelegationRequest(AIpinhoModel):
    delegation_id: str = Field(default_factory=lambda: f"delegation_{uuid4().hex}")
    parent_agent_id: str
    target_agent_id: str
    parent_session_id: str
    target_session_id: str | None = None
    parent_run_id: str
    child_run_id: str | None = None
    user_goal: str
    requested_operation: str
    operation_type: str
    workspace_id: str | None = None
    project_profile_id: str | None = None
    workspace_profile_id: str | None = None
    validation_profile_id: str | None = None
    command_profile_ids: list[str] = Field(default_factory=list)
    project_context_summary_sanitized: dict[str, Any] = Field(default_factory=dict)
    skill_id: str | None = None
    skill_version: str | None = None
    skill_inputs: dict[str, Any] = Field(default_factory=dict)
    expected_skill_outputs: list[str] = Field(default_factory=list)
    capabilities_requested: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: list[str] = Field(default_factory=list)
    memory_refs: list[str] = Field(default_factory=list)
    memory_context_sanitized: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "low"
    execution_mode: str = "governed_autorun"
    autoapproval_policy: dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = 900
    max_child_steps: int | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    updated_at: str = Field(default_factory=utc_now_iso)
    status: DelegationStatus = "created"
    evidence_refs: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class DelegationPolicyDecision(AIpinhoModel):
    policy_decision_id: str = Field(default_factory=lambda: f"delegation_policy_{uuid4().hex}")
    delegation_id: str
    parent_agent_id: str
    target_agent_id: str
    requested_operation: str
    capabilities_requested: list[str] = Field(default_factory=list)
    workspace_id: str | None = None
    project_profile_id: str | None = None
    workspace_profile_id: str | None = None
    validation_profile_id: str | None = None
    command_profile_ids: list[str] = Field(default_factory=list)
    project_context_summary_sanitized: dict[str, Any] = Field(default_factory=dict)
    skill_id: str | None = None
    skill_version: str | None = None
    skill_inputs: dict[str, Any] = Field(default_factory=dict)
    expected_skill_outputs: list[str] = Field(default_factory=list)
    workspace_role: str | None = None
    risk_level: str = "low"
    execution_mode: str = "governed_autorun"
    decision: DelegationDecision
    reason_code: str
    human_reason: str
    technical_reason_sanitized: str
    auto_approval_id: str | None = None
    approval_required: bool = False
    safe_alternative: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class DelegationResult(AIpinhoModel):
    delegation_id: str
    parent_run_id: str
    child_run_id: str | None = None
    parent_agent_id: str
    target_agent_id: str
    status: str
    summary: str
    reason_code: str | None = None
    files_read: list[str] = Field(default_factory=list)
    files_changed: list[str] = Field(default_factory=list)
    shell_commands: list[str] = Field(default_factory=list)
    artifacts: list[str] = Field(default_factory=list)
    memory_refs_used: list[str] = Field(default_factory=list)
    memory_refs_written: list[str] = Field(default_factory=list)
    memory_candidates_created: list[str] = Field(default_factory=list)
    validation_status: str | None = None
    report_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    completed_at: str | None = None
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class DelegationStatusResponse(AIpinhoModel):
    status: str
    delegation: DelegationRequest
    policy_decision: DelegationPolicyDecision | None = None
    result: DelegationResult | None = None
