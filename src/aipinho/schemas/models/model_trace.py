from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ModelTraceEvent(AIpinhoModel):
    event_id: str
    trace_id: str
    event_type: str
    status: str
    summary: str
    model_id: str | None = None
    data: dict[str, object] = Field(default_factory=dict)
    created_at: str
