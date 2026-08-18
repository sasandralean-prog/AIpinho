from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ModelDecisionTrace(AIpinhoModel):
    trace_id: str
    model_id: str | None = None
    decision: str
    reason: str
    warnings: list[str] = Field(default_factory=list)
    data: dict[str, object] = Field(default_factory=dict)
