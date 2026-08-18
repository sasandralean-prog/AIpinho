from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


PermissionDecisionValue = Literal["allowed", "ask", "denied"]


class OperationPermissionDecision(AIpinhoModel):
    action: str
    canonical_action: str
    permission: str
    decision: PermissionDecisionValue
    reason_code: str
    source: str = "workspace_permission_matrix"
    requires_approval: bool = False
    scope: dict[str, Any] = Field(default_factory=dict)


class OperationContract(AIpinhoModel):
    operation_id: str
    source_channel: str = "api"
    source_client: str = "unknown"
    session_id: str | None = None
    user_text: str = ""
    intent_type: str = "unknown"
    operation_type: str = "unknown"
    requested_actions: list[str] = Field(default_factory=list)
    normalized_actions: list[str] = Field(default_factory=list)
    negative_constraints: dict[str, bool] = Field(default_factory=dict)
    workspace_refs: list[str] = Field(default_factory=list)
    resolved_workspace_id: str | None = None
    resolved_workspace_path: str | None = None
    target_paths: list[str] = Field(default_factory=list)
    command: str | None = None
    patch: dict[str, Any] | None = None
    content: str | None = None
    risk_level: str = "low"
    permission_decisions: list[OperationPermissionDecision] = Field(default_factory=list)
    approval_required: bool = False
    approval_id: str | None = None
    execution_allowed: bool = False
    execution_plan: dict[str, Any] = Field(default_factory=dict)
    speaker_truth_requirements: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
