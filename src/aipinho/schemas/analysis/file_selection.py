from __future__ import annotations

from typing import Literal

from pydantic import Field

from aipinho.schemas.analysis.analysis_trace import AnalysisTraceItem
from aipinho.schemas.common.base import AIpinhoModel

FileSelectionStatus = Literal["ok", "partial", "blocked", "invalid"]


class FileSelectionRequest(AIpinhoModel):
    workspace: str
    goal: str = "general_project_analysis"
    semantic_query: str = ""
    root_role: str | None = None
    candidate_files: list[str] = Field(default_factory=list)
    focus_paths: list[str] = Field(default_factory=list)
    max_files: int | None = None
    max_total_bytes: int | None = None
    selection_budget_ms: int | None = None


class FileSelectionCandidate(AIpinhoModel):
    path: str
    score: int = 0
    reason: str = "candidate"
    size_bytes: int | None = None
    blocked: bool = False
    blocked_reason: str | None = None
    source_root_role: str | None = None
    entity_role: str | None = None
    inventory_eligible: bool = False
    inventory_reason: str | None = None
    routing_hints: list[str] = Field(default_factory=list)


class FileSelectionResult(AIpinhoModel):
    status: FileSelectionStatus
    selected_files: list[FileSelectionCandidate] = Field(default_factory=list)
    omitted_files: list[FileSelectionCandidate] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    trace: list[AnalysisTraceItem] = Field(default_factory=list)
    plan: dict[str, object] | None = None
