from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PromptAnalysisRequest(AIpinhoModel):
    prompt: str
    session_id: str | None = None
    context: dict[str, object] = Field(default_factory=dict)