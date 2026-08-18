from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class DebugTraceEvent(AIpinhoModel):
    event_id: str
    trace_id: str
    event_type: str
    status: str
    summary: str
    category: str = "debug"
    source: str | None = None
    sanitized: bool = True
    data: dict[str, object] = Field(default_factory=dict)
    created_at: str
