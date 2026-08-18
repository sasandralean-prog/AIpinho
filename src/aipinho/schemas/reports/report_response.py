from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.reports.project_report import ProjectReport


class ProjectReportResponse(AIpinhoModel):
    status: str
    report: ProjectReport | None = None
    rendered_markdown: str | None = None
    write_enabled: bool = False
    patch_enabled: bool = False
    shell_enabled: bool = False
    memory_write_enabled: bool = False
    rag_enabled: bool = False
    llm_required: bool = False
    warnings: list[str] = Field(default_factory=list)
    evaluation_status: str | None = None
    fallback_used: bool = False
    quality_gate_status: str | None = None


