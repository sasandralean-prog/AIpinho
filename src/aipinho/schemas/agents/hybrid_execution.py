from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


CodexExecutionMode = Literal[
    "codex_direct_executor",
    "codex_delegated_to_aipinho",
    "codex_hybrid_supervisor",
    "codex_observe_only",
]

IslandChatMode = Literal["chat", "delegate_to_aipinho", "artifact_text", "auto"]


class CodexModeSelectRequest(AIpinhoModel):
    user_prompt: str
    workspace: str | None = None
    risk_level: str = "low"
    requested_mode: CodexExecutionMode | None = None
    available_capabilities: list[str] = Field(default_factory=list)
    active_locks: list[dict[str, Any]] = Field(default_factory=list)


class CodexModeDecision(AIpinhoModel):
    selected_mode: CodexExecutionMode
    reason: str
    reason_code: str
    expected_owner_agent: str
    requires_lock: bool = False
    allowed_actions: list[str] = Field(default_factory=list)
    conflicting_lock_ids: list[str] = Field(default_factory=list)


class CodexDelegationRequest(AIpinhoModel):
    user_prompt: str
    workspace: str | None = None
    session_id: str | None = None
    requested_operation: str = "readonly_analysis"
    requested_capabilities: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: list[str] = Field(default_factory=lambda: ["human_summary", "event_trace"])
    risk_level: str = "low"


class CodexDiagnosticRequest(CodexDelegationRequest):
    requested_operation: str = "readonly_analysis"
    requested_capabilities: list[str] = Field(default_factory=lambda: ["read_workspace", "validation"])
    max_summary_items: int = Field(default=5, ge=1, le=20)


class CanonicalPromptRequest(AIpinhoModel):
    user_message: str
    source_agent: str
    workspace: str | None = None
    intent: str = "operational_request"
    constraints: dict[str, Any] = Field(default_factory=dict)
    desired_outputs: list[str] = Field(default_factory=list)
    validation_required: bool = True
    risk_level: str = "low"


class CanonicalPromptResult(AIpinhoModel):
    canonical_prompt: str
    requires_confirmation: bool = False
    risk_notes: list[str] = Field(default_factory=list)
    target_agent: str = "aipinho"
    mode: str = "governed_execution"


class IslandChatRequest(AIpinhoModel):
    session_id: str | None = None
    message: str
    workspace: str | None = None
    mode: IslandChatMode = "auto"
    intent: str = "conversation"
    operation_type: str = "chat"
    requested_capabilities: list[str] = Field(default_factory=list)
    constraints: dict[str, Any] = Field(default_factory=dict)
    desired_outputs: list[str] = Field(default_factory=list)
    artifact_filename: str | None = None


class IslandChatResponse(AIpinhoModel):
    message_id: str = Field(default_factory=lambda: f"island_message_{uuid4().hex}")
    response_text: str
    delegated: bool = False
    bridge_task_id: str | None = None
    artifact_refs: list[dict[str, Any]] = Field(default_factory=list)
    events_poll_url: str | None = None
    reason_code: str | None = None
    source_agent: str
    executor_agent: str | None = None
    raw_default_visible: bool = False


class DelegationLogSummary(AIpinhoModel):
    status: str
    top_errors: list[str] = Field(default_factory=list)
    files_touched: list[str] = Field(default_factory=list)
    commands: list[str] = Field(default_factory=list)
    exit_code: int | None = None
    artifact_refs: list[str] = Field(default_factory=list)
    recommended_next_steps: list[str] = Field(default_factory=list)
    full_log_artifact_id: str | None = None

