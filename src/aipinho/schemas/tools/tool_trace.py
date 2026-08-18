from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

ToolTraceSeverity = Literal["info", "warning", "error", "critical"]


class ToolTraceItem(AIpinhoModel):
    stage: str
    rule: str
    decision: str
    reason: str
    severity: ToolTraceSeverity = "info"
    source: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
