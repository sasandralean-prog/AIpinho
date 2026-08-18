from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class GenerationConfig(AIpinhoModel):
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 512
    stop: list[str] = Field(default_factory=list)
