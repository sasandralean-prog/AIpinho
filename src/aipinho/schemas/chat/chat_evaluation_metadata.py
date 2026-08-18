from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ChatEvaluationMetadata(AIpinhoModel):
    evaluation_id: str | None = None
    status: str | None = None
    score: float | None = None
    accepted: bool = False
    fallback_required: bool = False
    violations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
