from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.analysis.analysis_finding import AnalysisFinding
from aipinho.schemas.common.base import AIpinhoModel

AnalysisReportStatus = Literal["ok", "partial", "blocked", "invalid", "degraded"]


class AnalysisReport(AIpinhoModel):
    report_id: str
    status: AnalysisReportStatus
    title: str
    summary: str
    sections: list[dict[str, Any]] = Field(default_factory=list)
    findings: list[AnalysisFinding] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
