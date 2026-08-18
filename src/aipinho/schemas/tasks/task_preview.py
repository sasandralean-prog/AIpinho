from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.common.base import AIpinhoModel

TaskPreviewStatus = Literal["preview_ready", "approval_required", "blocked", "needs_clarification", "invalid"]


class TaskPreview(AIpinhoModel):
    preview_id: str
    draft_id: str
    session_id: str | None = None
    status: TaskPreviewStatus
    contract_type: str = "unknown"
    summary: str = ""
    requested_actions: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    denied_actions: list[str] = Field(default_factory=list)
    approval_required_for: list[str] = Field(default_factory=list)
    potential_side_effects: list[str] = Field(default_factory=list)
    operation_type: str = "unknown"
    runtime_profile: str | None = None
    executable_plan_ref: str | None = None
    expected_outcomes: list[str] = Field(default_factory=list)
    safe_to_execute: bool = False
    safe_to_preview: bool = False
    policy_snapshot: ApprovalPolicySnapshot
    trace: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str
    updated_at: str
