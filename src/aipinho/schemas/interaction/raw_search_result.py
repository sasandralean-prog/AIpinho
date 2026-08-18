from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class RawSearchResult(AIpinhoModel):
    raw_ref_id: str
    query: str
    total: int = 0
    matches: list[dict[str, object]] = Field(default_factory=list)
