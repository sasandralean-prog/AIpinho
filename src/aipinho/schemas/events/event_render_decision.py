from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class EventRenderDecision(AIpinhoModel):
    event_id: str | None = None
    event_type: str | None = None
    render_status: str
    reasons: list[str] = Field(default_factory=list)
