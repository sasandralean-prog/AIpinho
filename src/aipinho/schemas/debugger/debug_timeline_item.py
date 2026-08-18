from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class DebugTimelineItem(AIpinhoModel):
    trace_id: str
    event_id: str
    label: str
    status: str
    category: str
    timestamp: str
    data: dict[str, object] = Field(default_factory=dict)
