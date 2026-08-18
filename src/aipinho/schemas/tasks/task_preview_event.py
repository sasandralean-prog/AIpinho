from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

TaskPreviewEventType = Literal["preview_created", "policy_refreshed", "preview_invalidated"]


class TaskPreviewEvent(AIpinhoModel):
    event_id: str
    preview_id: str
    event_type: TaskPreviewEventType
    created_at: str
    summary: str
    data: dict[str, Any] = Field(default_factory=dict)