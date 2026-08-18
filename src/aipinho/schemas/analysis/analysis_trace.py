from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class AnalysisTraceItem(AIpinhoModel):
    stage: str
    status: str
    reason: str
    source: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
