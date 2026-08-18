from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class EventFilter(AIpinhoModel):
    event_types: list[str] = Field(default_factory=list)
    source_services: list[str] = Field(default_factory=list)
    severities: list[str] = Field(default_factory=list)
    statuses: list[str] = Field(default_factory=list)
    task_id: str | None = None
    session_id: str | None = None
    trace_id: str | None = None
    include_internal: bool = False
    include_hidden: bool = False
