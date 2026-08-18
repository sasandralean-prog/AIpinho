from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class SessionContext(AIpinhoModel):
    current_message: str = ""
    recent_summary: str = ""
    last_intent_type: str | None = None
    last_workspace_candidate: str | None = None
    active_task_draft_id: str | None = None
    constraints: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)