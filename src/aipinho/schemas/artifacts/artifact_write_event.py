from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ArtifactWriteEvent(AIpinhoModel):
    event_id: str
    write_run_id: str
    event_type: str
    status: str = "ok"
    summary: str = ""
    created_at: str
    data: dict[str, object] = Field(default_factory=dict)
