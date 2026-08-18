from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchApplyEvent(AIpinhoModel):
    event_id: str
    apply_run_id: str
    event_type: str
    created_at: str
    summary: str
    data: dict[str, object] = Field(default_factory=dict)
