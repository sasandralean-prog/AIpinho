from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class AmbiguityResult(AIpinhoModel):
    is_ambiguous: bool = False
    requires_clarification: bool = False
    reasons: list[str] = Field(default_factory=list)
    clarifying_question: str | None = None