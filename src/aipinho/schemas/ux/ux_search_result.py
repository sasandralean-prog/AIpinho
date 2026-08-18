from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class UXSearchResult(AIpinhoModel):
    query: str
    total: int = 0
    matches: list[dict[str, object]] = Field(default_factory=list)
