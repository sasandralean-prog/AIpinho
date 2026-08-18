from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.analysis.file_selection import FileSelectionCandidate, FileSelectionResult
from aipinho.schemas.analysis.project_analysis_budget import ProjectAnalysisBudget
from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.schemas.tools.tool_execution_result import ToolExecutionResult
from aipinho.services.analysis.file_context_builder import FileContextBuilder
from aipinho.services.analysis.project_analysis_service import ProjectAnalysisService


class FixedTree:
    def __init__(self, files: list[str]) -> None:
        self.files = files

    def build_tree_summary(self, request, *, progress=None):
        if progress:
            progress("before_path_resolution", {"workspace": request.workspace})
            progress("after_path_resolution", {"current_root": request.workspace})
            progress("before_workspace_root_scan", {"current_root": request.workspace})
            progress("after_workspace_root_scan", {"current_root": request.workspace})
            progress(
                "after_file_enumeration",
                {"files_scan_attempted": len(self.files), "files_scanned": len(self.files), "files_discovered": len(self.files)},
            )
        return ProjectTreeSummary(
            workspace=request.workspace,
            status="ok",
            total_files_seen=len(self.files),
            candidate_files=list(self.files),
        )

    def status(self):
        return {"status": "ok"}


class FixedSelection:
    def __init__(self, candidates: list[FileSelectionCandidate]) -> None:
        self.candidates = candidates

    def select_files(self, request, *, project_tree=None, progress=None):
        if progress:
            progress("project_analysis_selection_started", {"candidate_count": len(self.candidates)})
            progress("project_analysis_selection_finished", {"candidate_count": len(self.candidates), "selected": len(self.candidates), "omitted": 0})
        return FileSelectionResult(status="ok", selected_files=list(self.candidates))

    def status(self):
        return {"status": "ok"}


class BoundedReadExecution:
    def __init__(self) -> None:
        self.max_bytes_requested: list[int] = []

    def execute(self, request):
        max_bytes = int(request.input.get("max_bytes") or 0)
        path = str(request.input.get("path") or "")
        self.max_bytes_requested.append(max_bytes)
        return ToolExecutionResult(
            execution_id=f"exec_{uuid4().hex}",
            tool_id=request.tool_id,
            status="executed_readonly",
            workspace=str(request.input.get("workspace") or ""),
            target_path=path,
            content="x" * max(0, min(max_bytes, 64)),
            content_truncated=max_bytes < 30_000,
            metadata={"bytes_read": max_bytes, "size": 30_000, "extension": path.rsplit(".", 1)[-1] if "." in path else ""},
            side_effects=False,
            safe_to_execute=False,
        )

    def status(self):
        return {"status": "ok"}


def test_expensive_file_gets_bounded_partial_read_before_single_file_budget_blocks(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_PROJECT_ANALYSIS_MAX_SINGLE_FILE_READ_MS", "1")
    execution = BoundedReadExecution()
    service = ProjectAnalysisService(
        tree_service=FixedTree(["src/core/Main.txt"]),  # type: ignore[arg-type]
        selection_service=FixedSelection([FileSelectionCandidate(path="src/core/Main.txt", score=100, size_bytes=30_000)]),  # type: ignore[arg-type]
        context_builder=FileContextBuilder(execution=execution),
        budget=ProjectAnalysisBudget(max_total_seconds=30, max_files_read=1, max_bytes_read=120_000),
    )

    result = service.analyze_project(ProjectAnalysisRequest(workspace=str(tmp_path), max_file_bytes=30_000))

    assert result.status in {"ok", "partial", "degraded"}
    assert result.reason_code in {"PROJECT_ANALYSIS_COMPLETED", "PROJECT_ANALYSIS_DEGRADED"}
    assert result.files_partial_read == 1
    assert result.read_decisions[0]["decision"] == "partial_read"
    assert result.read_decisions[0]["reason_code"] == "PROJECT_ANALYSIS_FILE_PARTIAL_READ_BY_BUDGET"
    assert execution.max_bytes_requested[0] < 30_000
    assert result.safe_to_continue is True


def test_file_skipped_when_remaining_context_budget_cannot_hold_minimum_sample(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_PROJECT_ANALYSIS_MAX_SINGLE_FILE_READ_MS", "1")
    execution = BoundedReadExecution()
    candidates = [
        FileSelectionCandidate(path="src/core/A.txt", score=100, size_bytes=500),
        FileSelectionCandidate(path="src/core/B.txt", score=90, size_bytes=500),
    ]
    service = ProjectAnalysisService(
        tree_service=FixedTree([item.path for item in candidates]),  # type: ignore[arg-type]
        selection_service=FixedSelection(candidates),  # type: ignore[arg-type]
        context_builder=FileContextBuilder(execution=execution),
        budget=ProjectAnalysisBudget(max_total_seconds=30, max_files_read=2, max_bytes_read=1_100),
    )

    result = service.analyze_project(ProjectAnalysisRequest(workspace=str(tmp_path), max_file_bytes=3_000, max_total_bytes=1_500))

    assert result.files_read == 1
    assert result.files_skipped == 1
    assert result.read_decisions[1]["decision"] == "skip"
    assert result.read_decisions[1]["reason_code"] == "PROJECT_ANALYSIS_FILE_SKIPPED_BY_BUDGET"
    assert result.skipped_files_summary["PROJECT_ANALYSIS_FILE_SKIPPED_BY_BUDGET"] == 1
    assert result.safe_to_continue is True


def test_single_file_budget_no_longer_blocks_when_partial_context_is_sufficient(tmp_path, monkeypatch):
    monkeypatch.setenv("AIPINHO_PROJECT_ANALYSIS_MAX_SINGLE_FILE_READ_MS", "1")
    execution = BoundedReadExecution()
    service = ProjectAnalysisService(
        tree_service=FixedTree(["src/core/Main.txt"]),  # type: ignore[arg-type]
        selection_service=FixedSelection([FileSelectionCandidate(path="src/core/Main.txt", score=100, size_bytes=30_000)]),  # type: ignore[arg-type]
        context_builder=FileContextBuilder(execution=execution),
        budget=ProjectAnalysisBudget(max_total_seconds=30, max_files_read=1, max_bytes_read=120_000),
    )

    result = service.analyze_project(ProjectAnalysisRequest(workspace=str(tmp_path), max_file_bytes=30_000))

    assert result.reason_code != "PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED"
    assert result.safe_to_continue is True
    assert result.partial_readiness is not None
    assert result.partial_readiness["safe_to_continue_to_artifact_runtime"] is True
