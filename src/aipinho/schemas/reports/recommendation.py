from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class Recommendation(AIpinhoModel):
    recommendation_id: str
    finding_id: str | None = None
    title: str
    summary: str
    requires_write: bool = False
    requires_followup: bool = False
    safe_next_actions: list[str] = Field(default_factory=list)
