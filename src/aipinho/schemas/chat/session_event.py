from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

SessionEventType = Literal[
    "session_created",
    "chat_message",
    "intent_analyzed",
    "policy_preview",
    "task_draft_created",
    "blocked",
    "clarification_requested",
    "session_deleted",
    "operational_context_updated",
]


class SessionEvent(AIpinhoModel):
    event_id: str
    session_id: str
    event_type: SessionEventType
    created_at: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
