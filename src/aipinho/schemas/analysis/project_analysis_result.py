from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from aipinho.schemas.analysis.analysis_finding import AnalysisFinding
from aipinho.schemas.analysis.analysis_report import AnalysisReport
from aipinho.schemas.analysis.analysis_trace import AnalysisTraceItem
from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.schemas.common.base import AIpinhoModel

ProjectAnalysisStatus = Literal["ok", "partial", "blocked", "invalid", "degraded", "failed", "cancelled", "timeout"]


class ProjectAnalysisResult(AIpinhoModel):
    result_id: str
    workspace: str
    status: ProjectAnalysisStatus
    tree_summary: ProjectTreeSummary
    file_context: FileContextBundle
    structures: list[str] = Field(default_factory=list)
    findings: list[AnalysisFinding] = Field(default_factory=list)
    report: AnalysisReport
    warnings: list[str] = Field(default_factory=list)
    violations: list[str] = Field(default_factory=list)
    trace: list[AnalysisTraceItem] = Field(default_factory=list)
    reason_code: str | None = None
    error_type: str | None = None
    error_message: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    duration_ms: int | None = None
    last_checkpoint: str | None = None
    last_completed_checkpoint: str | None = None
    elapsed_ms_by_checkpoint: dict[str, int] = Field(default_factory=dict)
    files_discovered: int = 0
    files_scan_attempted: int = 0
    files_scanned: int = 0
    files_read: int = 0
    files_partial_read: int = 0
    files_skipped: int = 0
    bytes_read: int = 0
    bytes_skipped_estimated: int = 0
    read_decisions: list[dict[str, Any]] = Field(default_factory=list)
    current_root: str | None = None
    current_path_sample: str | None = None
    blocking_operation: str | None = None
    budget_exceeded_at: str | None = None
    findings_count: int = 0
    semantic_evidence_count: int = 0
    dependency_edges_count: int = 0
    partial: bool = False
    budget: dict[str, Any] = Field(default_factory=dict)
    budget_cooperation_policy: dict[str, Any] = Field(default_factory=dict)
    file_selection_plan: dict[str, Any] | None = None
    file_read_plan: dict[str, Any] | None = None
    partial_readiness: dict[str, Any] | None = None
    corpus_handoff: dict[str, Any] | None = None
    files_selected: int = 0
    skipped_files_summary: dict[str, int] = Field(default_factory=dict)
    elapsed_ms_by_stage: dict[str, int] = Field(default_factory=dict)
    remaining_budget_ms_at_return: int | None = None
    handoff_reserve_reached: bool = False
    limitations: list[str] = Field(default_factory=list)
    budget_exceeded: bool = False
    cancel_requested: bool = False
    safe_to_continue: bool = True
