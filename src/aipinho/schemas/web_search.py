from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


WebSearchStatus = Literal["ready", "blocked", "failed", "capability_missing", "timeout"]


class WebSearchSource(AIpinhoModel):
    title: str
    url: str
    snippet: str
    source_name: str | None = None
    published_at: str | None = None
    retrieved_at: str
    reliability_hint: str | None = None


class WebSearchResult(AIpinhoModel):
    status: WebSearchStatus
    query: str
    provider_id: str
    results: list[WebSearchSource] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    reason_code: str | None = None
    source_count: int = 0
    searched_at: str

