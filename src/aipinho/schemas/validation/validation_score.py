from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ValidationScore(AIpinhoModel):
    score: float
    status: str
    penalties_applied: list[str] = Field(default_factory=list)
    critical_overrides: list[str] = Field(default_factory=list)
