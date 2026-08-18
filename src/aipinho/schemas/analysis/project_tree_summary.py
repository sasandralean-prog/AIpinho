from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.analysis.analysis_trace import AnalysisTraceItem
from aipinho.schemas.common.base import AIpinhoModel

TreeSummaryStatus = Literal["ok", "partial", "blocked", "invalid", "degraded"]


class ProjectTreeSummary(AIpinhoModel):
    workspace: str
    status: TreeSummaryStatus
    root_name: str | None = None
    total_files_seen: int = 0
    total_dirs_seen: int = 0
    top_level: list[str] = Field(default_factory=list)
    important_paths: list[str] = Field(default_factory=list)
    candidate_files: list[str] = Field(default_factory=list)
    ignored_paths: list[str] = Field(default_factory=list)
    blocked_paths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    trace: list[AnalysisTraceItem] = Field(default_factory=list)
