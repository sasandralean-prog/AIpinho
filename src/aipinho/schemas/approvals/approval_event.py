from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

ApprovalEventType = Literal[
    "approval_created",
    "approval_preview_created",
    "approval_approved",
    "approval_rejected",
    "approval_cancelled",
    "approval_batch_approved",
    "approval_batch_denied",
    "approval_runtime_context_attached",
    "approval_expired",
    "approval_invalidated",
    "approval_not_created_no_executable_plan",
    "approval_approved_but_no_executable_plan",
    "policy_refreshed",
    "artifact_preview_sync_failed",
    "chat_approval_command_detected",
    "approval_decision_received_from_chat",
    "approval_decision_accepted",
    "approval_decision_rejected",
    "approval_ambiguous_decision",
    "approval_preview_requested_from_chat",
    "approval_risks_requested_from_chat",
    "approval_policy_requested_from_chat",
    "approval_diff_requested_from_chat",
    "approval_command_requested_from_chat",
    "approval_files_requested_from_chat",
    "approval_request_created",
    "continue_approval_required",
    "continue_approval_decision_received",
    "permission_grant_requested",
    "permission_grant_previewed",
    "config_change_request_created",
    "universal_approver_registered",
    "universal_approval_decision_received",
    "universal_approval_decision_accepted",
    "universal_approval_decision_rejected",
    "universal_approval_capability_denied",
    "universal_approval_trust_denied",
    "universal_approval_signature_created",
]


class ApprovalEvent(AIpinhoModel):
    event_id: str
    approval_id: str
    event_type: ApprovalEventType
    created_at: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
