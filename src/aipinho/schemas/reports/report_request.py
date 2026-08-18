from __future__ import annotations

from typing import Literal
from typing import Any

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel

ReportGoal = Literal["architecture_overview", "policy_audit", "codebase_overview", "security_readonly", "general"]
ReportChannel = Literal["chat", "artifact_preview"]
ReportFormat = Literal["markdown", "json"]


class ProjectReportOutput(AIpinhoModel):
    channel: ReportChannel = "chat"
    format: ReportFormat = "markdown"
    save_file: bool = False
    target_path: str | None = None


class ProjectReportLimits(AIpinhoModel):
    max_findings: int = 50
    max_evidence_per_finding: int = 5
    max_report_chars: int = 20000


class ProjectReportRequest(AIpinhoModel):
    workspace: str | None = None
    goal: ReportGoal = "general"
    analysis_id: str | None = None
    context_bundle_id: str | None = None
    include_sections: list[str] = Field(default_factory=lambda: ["executive_summary", "architecture", "policies", "routes", "schemas", "services", "tests", "risks", "recommendations", "limitations"])
    output: ProjectReportOutput = Field(default_factory=ProjectReportOutput)
    limits: ProjectReportLimits = Field(default_factory=ProjectReportLimits)
    include_trace: bool = False
    requested_deliverables: list[str] = Field(default_factory=list)
    workspace_references: list[dict[str, Any]] = Field(default_factory=list)


class ReportFromAnalysisRequest(AIpinhoModel):
    analysis_id: str
    workspace: str | None = None
    goal: ReportGoal = "general"
    include_trace: bool = False
