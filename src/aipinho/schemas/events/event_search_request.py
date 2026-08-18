from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class EventSearchRequest(AIpinhoModel):
    query: str = ""
    filters: dict[str, object] = Field(default_factory=dict)
    limit: int = 100
