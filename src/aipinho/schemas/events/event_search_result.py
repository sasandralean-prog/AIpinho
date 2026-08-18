from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class EventSearchResult(AIpinhoModel):
    query: str
    total: int
    events: list[dict[str, object]] = Field(default_factory=list)
