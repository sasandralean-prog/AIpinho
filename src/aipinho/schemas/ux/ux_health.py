from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

class UXHealth(AIpinhoModel):
    state: str = "healthy"
    degraded_states: list[dict[str, object]] = Field(default_factory=list)
    offline: bool = False
    last_successful_snapshot: dict[str, object] | None = None
    warnings: list[str] = Field(default_factory=list)
