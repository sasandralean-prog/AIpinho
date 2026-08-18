from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.reports.report_trace import ReportTraceItem

ArtifactPreviewStatus = Literal["preview_ready", "blocked", "invalid"]


class ReportArtifactPreviewRequest(AIpinhoModel):
    report_id: str
    workspace: str | None = None
    target_path: str = "reports/project_report.md"
    format: str = "markdown"


class ReportArtifactPreview(AIpinhoModel):
    preview_id: str
    report_id: str
    status: ArtifactPreviewStatus
    target_path: str
    content_preview: str
    would_write: bool = True
    requires_approval: bool = True
    safe_to_execute: bool = False
    warnings: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    trace: list[ReportTraceItem] = Field(default_factory=list)
