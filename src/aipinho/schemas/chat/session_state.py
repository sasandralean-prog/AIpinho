from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.chat.chat_message import ChatMessage
from aipinho.schemas.common.base import AIpinhoModel


class SessionState(AIpinhoModel):
    session_id: str
    status: str = "active"
    created_at: str
    updated_at: str
    expires_at: str | None = None
    surface: str = "unknown"
    recent_messages: list[ChatMessage] = Field(default_factory=list)
    last_intent_map: dict[str, Any] = Field(default_factory=dict)
    last_policy_decision: dict[str, Any] = Field(default_factory=dict)
    active_workspace_candidate: str | None = None
    active_task_draft_id: str | None = None
    last_operational_context: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    trace_refs: list[str] = Field(default_factory=list)
