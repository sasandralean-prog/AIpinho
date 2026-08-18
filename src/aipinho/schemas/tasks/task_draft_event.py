from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

TaskDraftEventType = Literal["draft_created", "policy_refreshed", "draft_deleted"]


class TaskDraftEvent(AIpinhoModel):
    event_id: str
    draft_id: str
    event_type: TaskDraftEventType
    created_at: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)