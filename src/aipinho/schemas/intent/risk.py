from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

RiskLevel = Literal["low", "medium", "high", "critical"]


class RiskResult(AIpinhoModel):
    level: RiskLevel = "low"
    reasons: list[str] = Field(default_factory=list)