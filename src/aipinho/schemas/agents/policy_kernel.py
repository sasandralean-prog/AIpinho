from __future__ import annotations

from typing import Any
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.events.contracts import utc_now_iso


class AutoApprovalDecision(AIpinhoModel):
    auto_approval_id: str = Field(default_factory=lambda: f"auto_approval_{uuid4().hex}")
    policy_decision_id: str
    agent_id: str
    session_id: str
    run_id: str
    tool_invocation_id: str | None = None
    action_type: str
    capability: str
    workspace_id: str | None = None
    workspace_role: str | None = None
    risk_level: str
    execution_mode: str
    approved: bool
    reason_code: str
    human_reason: str
    technical_reason_sanitized: str
    created_at: str = Field(default_factory=utc_now_iso)
    evidence_refs: list[str] = Field(default_factory=list)


class SafeAction(AIpinhoModel):
    action_id: str = Field(default_factory=lambda: f"safe_action_{uuid4().hex}")
    label: str
    kind: str
    agent_id: str
    session_id: str
    run_id: str
    tool_invocation_id: str | None = None
    approval_id: str | None = None
    endpoint_ref: str | None = None
    method: str = "POST"
    side_effect: str = "none"
    requires_confirmation: bool = True
    human_explanation: str
    risk_level: str
    expires_at: str | None = None


class AgentPolicyProfile(AIpinhoModel):
    agent_id: str
    role: str
    default_mode: str = "governed_autorun"
    can_use_tool_gateway: bool = True
    can_execute_local: bool = False
    can_delegate_future: bool = False
    direct_local_write: bool = True
    prefer_delegate_to_aipinho: bool = False
    prefer_delegate_to_codex_or_aipinho: bool = False
    autoapprove_read: bool = True
    autoapprove_artifacts: bool = True
    autoapprove_target_write: bool = True
    autoapprove_readonly_shell: bool = True
    autoapprove_test_shell: bool = True
    autoapprove_build_shell: bool = True
    block_destructive_shell: bool = True
    block_git_write_by_default: bool = True
    block_network_shell_by_default: bool = True
    block_secret_access: bool = True
    block_source_readonly_write: bool = True
    metadata_sanitized: dict[str, Any] = Field(default_factory=dict)


class BlockReasonDefinition(AIpinhoModel):
    reason_code: str
    human_reason: str
    safe_alternative: str | None = None
    severity: str = "warning"


class PolicyKernelStatus(AIpinhoModel):
    status: str
    profiles_loaded: int
    block_reason_codes_loaded: int
    default_execution_mode: str
    power_user_enabled: bool
    unrestricted_local_lab_enabled: bool
