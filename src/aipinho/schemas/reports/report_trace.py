from __future__ import annotations

from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ReportTraceItem(AIpinhoModel):
    stage: str
    status: str
    reason: str
    rule_id: str | None = None
    source: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
