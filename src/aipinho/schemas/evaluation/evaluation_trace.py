from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

EvaluationTraceStatus = Literal["ok", "warning", "blocked", "degraded", "error"]


class EvaluationTraceItem(AIpinhoModel):
    stage: str
    status: EvaluationTraceStatus = "ok"
    reason: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    source: str | None = None
