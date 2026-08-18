from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

FindingSeverity = Literal["info", "low", "medium", "high", "blocked"]


class AnalysisFinding(AIpinhoModel):
    finding_id: str
    category: str
    severity: FindingSeverity = "info"
    title: str
    summary: str
    evidence_paths: list[str] = Field(default_factory=list)
    recommendation: str | None = None
