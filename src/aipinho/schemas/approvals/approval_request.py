from __future__ import annotations

from pydantic import Field

from aipinho.schemas.approvals.universal_approver import ApprovalOrigin, ApprovalSignature
from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.approvals.approval_state import ApprovalScope, ApprovalStatus
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.common.base import AIpinhoModel


class ApprovalRequest(AIpinhoModel):
    approval_id: str
    preview_id: str
    draft_id: str
    run_id: str | None = None
    task_id: str | None = None
    session_id: str | None = None
    agent_id: str = "aipinho"
    workspace_id: str | None = None
    workspace_path: str | None = None
    operation_type: str = "unknown"
    contract_type: str = "unknown"
    runtime_profile: str | None = None
    target_paths: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    expected_outcomes: list[str] = Field(default_factory=list)
    executable_plan_ref: str | None = None
    execution_id: str | None = None
    execution_plan_snapshot: dict[str, object] = Field(default_factory=dict)
    preview_hash: str | None = None
    policy_snapshot_hash: str | None = None
    resume_status: str | None = None
    block_reason_code: str | None = None
    preview: dict[str, object] = Field(default_factory=dict)
    policy_refs: list[str] = Field(default_factory=list)
    allowed_by_policy: bool = True
    forbidden_operations: list[str] = Field(default_factory=list)
    status: ApprovalStatus = "pending"
    actions_requested: list[str] = Field(default_factory=list)
    approval_scope: ApprovalScope = "future_execution"
    reason: str = ""
    risk_level: str = "unknown"
    policy_snapshot: ApprovalPolicySnapshot
    expires_at: str
    created_at: str
    updated_at: str
    created_by: Actor = Field(default_factory=Actor)
    approval_origin: ApprovalOrigin | None = None
    approval_signature: ApprovalSignature | None = None
    approval_authority: str = "AIpinho"
    trace: list[dict[str, object]] = Field(default_factory=list)
    execution_status: str = "not_executed"
