from __future__ import annotations
from typing import Any
from pydantic import Field
from aipinho.schemas.common.base import AIpinhoModel

class ReportQualityResult(AIpinhoModel):
    validation_id: str
    report_id: str | None = None
    status: str
    score: float
    safe_to_display: bool = True
    warnings: list[str] = Field(default_factory=list)
    blocking_findings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
