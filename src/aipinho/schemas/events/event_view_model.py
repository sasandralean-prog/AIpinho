from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class EventViewModel(AIpinhoModel):
    event_id: str
    title: str
    summary: str
    severity: str = "info"
    status: str = "created"
    visibility: str = "public"
    copy_available: bool = True
    raw_available: bool = False
    render_decision: dict[str, object] = Field(default_factory=dict)
