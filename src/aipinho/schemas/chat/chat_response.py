from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.chat.chat_trace import ChatTraceItem
from aipinho.schemas.common.base import AIpinhoModel

ChatResponseStatus = Literal[
    "ok",
    "ready",
    "needs_clarification",
    "blocked",
    "pending_approval",
    "preview",
    "degraded",
    "error",
    "failed",
    "accepted_running",
    "timeout_blocked",
]
ChatMessageType = Literal[
    "assistant_final_answer",
    "assistant_degraded_answer",
    "task_preview",
    "task_status_update",
    "artifact_offer",
    "artifact_preview",
    "system_diagnostic_result",
    "clarification_request",
    "blocked_policy_message",
]


class ChatNextAction(AIpinhoModel):
    type: str
    label: str
    target_id: str | None = None


class ChatArtifactLink(AIpinhoModel):
    artifact_id: str
    filename: str
    content_type: str
    size_bytes: int | None = None
    download_endpoint: str
    download_path: str
    label: str = "Baixar artifact"
    requires_token: bool = True


class ChatPolicyBlock(AIpinhoModel):
    block_id: str
    operation_id: str
    session_id: str | None = None
    task_id: str | None = None
    operation_type: str
    requested_capability: str | None = None
    requested_action: str | None = None
    workspace_id: str | None = None
    workspace_role: str | None = None
    policy_name: str
    policy_decision_id: str | None = None
    block_reason_code: str
    human_reason: str
    safe_alternatives: list[str] = Field(default_factory=list)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    trace_id: str | None = None
    event_id: str | None = None
    requires_user_action: bool = False
    blocked_stage: str | None = None
    technical_reason_sanitized: str | None = None
    source_read_status: str | None = None
    artifact_output_status: str | None = None
    approval_status: str | None = None
    validation_status: str | None = None
    validation_id: str | None = None


class ChatResponse(AIpinhoModel):
    response_id: str
    session_id: str | None = None
    task_draft_id: str | None = None
    preview_id: str | None = None
    task_id: str | None = None
    task_run_id: str | None = None
    approval_id: str | None = None
    task_preview_id: str | None = None
    artifact_id: str | None = None
    artifact_preview_id: str | None = None
    artifact_links: list[ChatArtifactLink] = Field(default_factory=list)
    result_ref_id: str | None = None
    operation_id: str | None = None
    operation_type: str | None = None
    message_type: ChatMessageType = "assistant_final_answer"
    status: ChatResponseStatus
    message: str
    intent: dict[str, Any] = Field(default_factory=dict)
    policy: dict[str, Any] = Field(default_factory=dict)
    contract_preview: dict[str, Any] = Field(default_factory=dict)
    actions: list[str] = Field(default_factory=list)
    next_actions: list[ChatNextAction] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[ChatTraceItem] = Field(default_factory=list)
    raw_debug_ref: str | None = None
    model_used: str | None = None
    real_inference: bool | None = None
    model_warnings: list[str] = Field(default_factory=list)
    evaluation_status: str | None = None
    evaluation_warnings: list[str] = Field(default_factory=list)
    fallback_used: bool = False
    context_plan_id: str | None = None
    citation_map: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    requires_user_action: bool = False
    is_final_answer: bool = True
    grounded: bool = True
    grounding_required: bool = False
    grounding_missing_reason: str | None = None
    policy_block: ChatPolicyBlock | None = None
    governance_lifecycle: dict[str, Any] = Field(default_factory=dict)

