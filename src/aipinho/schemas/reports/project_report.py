from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.reports.evidence_citation import EvidenceCitation
from aipinho.schemas.reports.evidence_finding import EvidenceFinding
from aipinho.schemas.reports.recommendation import Recommendation
from aipinho.schemas.reports.report_section import ReportSection
from aipinho.schemas.reports.report_trace import ReportTraceItem

ProjectReportStatus = Literal["completed", "partial", "blocked", "degraded"]


class ProjectReport(AIpinhoModel):
    report_id: str
    workspace: str
    goal: str
    status: ProjectReportStatus
    generated_at: str
    source_analysis_id: str | None = None
    source_context_bundle_id: str | None = None
    executive_summary: str
    sections: list[ReportSection] = Field(default_factory=list)
    findings: list[EvidenceFinding] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    evidence_index: list[EvidenceCitation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[ReportTraceItem] = Field(default_factory=list)
    quality_gate: dict | None = None
    requested_deliverables: list[str] = Field(default_factory=list)
    fulfilled_deliverables: list[str] = Field(default_factory=list)
    missing_deliverables: list[str] = Field(default_factory=list)

