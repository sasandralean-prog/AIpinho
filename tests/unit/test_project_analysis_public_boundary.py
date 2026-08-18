from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.analysis.analysis_report import AnalysisReport
from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.project_analysis_budget import ProjectAnalysisBudget
from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.schemas.analysis.project_analysis_result import ProjectAnalysisResult
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.services.analysis.project_analysis_service import ProjectAnalysisService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    ReadonlyAnalysisArtifactRuntimeService,
)
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


def _blocked_project_analysis(workspace: str, reason_code: str = "PROJECT_ANALYSIS_TIMEOUT") -> ProjectAnalysisResult:
    return ProjectAnalysisResult(
        result_id=f"project_analysis_{uuid4().hex}",
        workspace=workspace,
        status="timeout",
        tree_summary=ProjectTreeSummary(workspace=workspace, status="blocked", warnings=[reason_code]),
        file_context=FileContextBundle(bundle_id=f"file_context_{uuid4().hex}", workspace=workspace, status="blocked"),
        report=AnalysisReport(
            report_id=f"analysis_report_{uuid4().hex}",
            status="blocked",
            title="Project Analysis Boundary",
            summary="Project analysis stopped at a governed boundary.",
        ),
        reason_code=reason_code,
        error_message="Project analysis stopped at a governed boundary.",
        safe_to_continue=False,
        budget={"max_total_seconds": 0.001},
        budget_exceeded=True,
    )


def _partial_project_analysis(workspace: str) -> ProjectAnalysisResult:
    reason_code = "PROJECT_ANALYSIS_PARTIAL_HANDOFF"
    return ProjectAnalysisResult(
        result_id=f"project_analysis_{uuid4().hex}",
        workspace=workspace,
        status="partial",
        tree_summary=ProjectTreeSummary(workspace=workspace, status="partial", candidate_files=["src/App.kt"]),
        file_context=FileContextBundle(bundle_id=f"file_context_{uuid4().hex}", workspace=workspace, status="partial"),
        report=AnalysisReport(
            report_id=f"analysis_report_{uuid4().hex}",
            status="partial",
            title="Project Analysis Partial Handoff",
            summary="Project analysis returned partial context.",
        ),
        reason_code=reason_code,
        safe_to_continue=True,
        partial=True,
        files_discovered=1,
        files_selected=1,
        files_read=0,
        bytes_read=0,
        remaining_budget_ms_at_return=1500,
        handoff_reserve_reached=True,
        partial_readiness={
            "safe_to_continue_to_artifact_runtime": True,
            "minimum_context_available": True,
            "workspace_root_resolved": True,
            "tree_summary_available": True,
            "file_selection_available": True,
            "file_context_available": False,
            "contract_context_available": True,
            "known_limitations": ["file_context_partial"],
            "missing_context": ["file_context"],
            "reason_codes": ["PROJECT_ANALYSIS_PARTIAL_CONTEXT_AVAILABLE", reason_code],
            "confidence": 0.62,
        },
    )


class BoundaryBlockedAnalysis:
    def analyze_project(self, request: ProjectAnalysisRequest, *, cancel_requested=None) -> ProjectAnalysisResult:
        return _blocked_project_analysis(request.workspace)


class OpaqueFailureAnalysis:
    def analyze_project(self, request: ProjectAnalysisRequest, *, cancel_requested=None) -> ProjectAnalysisResult:
        raise ValueError()


class PartialAnalysis:
    def analyze_project(self, request: ProjectAnalysisRequest, *, cancel_requested=None) -> ProjectAnalysisResult:
        return _partial_project_analysis(request.workspace)


def test_project_analysis_service_returns_governed_timeout_not_raw_exception(tmp_path):
    service = ProjectAnalysisService(budget=ProjectAnalysisBudget(max_total_seconds=0.0))

    result = service.analyze_project(ProjectAnalysisRequest(workspace=str(tmp_path), prompt="analise"))

    assert result.status == "timeout"
    assert result.reason_code == "PROJECT_ANALYSIS_PATH_RESOLUTION_TIMEOUT"
    assert result.last_checkpoint == "before_path_resolution"
    assert result.budget_exceeded_at == "before_path_resolution"
    assert result.safe_to_continue is False
    assert result.finished_at is not None
    assert result.error_message


def test_readonly_runtime_blocks_before_artifacts_with_explicit_artifact_state(tmp_path, task_runtime_store):
    runtime = TaskRuntimeService(store=task_runtime_store)
    service = ReadonlyAnalysisArtifactRuntimeService(
        runtime=runtime,
        analysis=BoundaryBlockedAnalysis(),  # type: ignore[arg-type]
    )

    execution = service.execute(
        request=ChatRequest(
            message="Fase 1 gere artifact reports/firetest5/music_inventory.csv",
            session_id="chat_project_boundary",
        ),
        workspace=str(tmp_path),
    )
    result = task_runtime_store.get_result(execution.run_id)
    session = UniversalTaskSessionService(store=task_runtime_store, approvals=runtime.approvals).artifacts_for_run(execution.run_id)

    assert execution.response.status == "blocked"
    assert result is not None
    assert result.status == "blocked"
    assert result.outputs["artifact_result"]["artifact_state"]["status"] == "blocked_before_artifact_creation"
    assert result.outputs["validation_result"]["phase"] == "project_analysis"
    assert session is not None
    assert session["artifact_state"]["status"] == "blocked_before_artifact_creation"
    assert session["artifact_state"]["reason_code"] == "PROJECT_ANALYSIS_TIMEOUT"
    assert not any(event.type == "artifact_created" for event in task_runtime_store.get_events(execution.run_id))


def test_readonly_runtime_preserves_opaque_project_analysis_error_message(tmp_path, task_runtime_store):
    runtime = TaskRuntimeService(store=task_runtime_store)
    service = ReadonlyAnalysisArtifactRuntimeService(
        runtime=runtime,
        analysis=OpaqueFailureAnalysis(),  # type: ignore[arg-type]
    )

    execution = service.execute(
        request=ChatRequest(
            message="Fase 1 gere artifact reports/firetest5/music_inventory.csv",
            session_id="chat_project_failure",
        ),
        workspace=str(tmp_path),
    )
    result = task_runtime_store.get_result(execution.run_id)

    assert result is not None
    assert result.outputs["validation_result"]["error_type"] == "ValueError"
    assert result.outputs["validation_result"]["error_message"] == "ValueError"


def test_readonly_runtime_advances_to_artifact_started_only_for_safe_partial_project_analysis(tmp_path, task_runtime_store):
    runtime = TaskRuntimeService(store=task_runtime_store)
    service = ReadonlyAnalysisArtifactRuntimeService(
        runtime=runtime,
        analysis=PartialAnalysis(),  # type: ignore[arg-type]
    )

    execution = service.execute(
        request=ChatRequest(
            message="Fase 1 gere artifact reports/firetest5/phase1_discovery.md",
            session_id="chat_project_partial",
        ),
        workspace=str(tmp_path),
    )
    events = task_runtime_store.get_events(execution.run_id)
    result = task_runtime_store.get_result(execution.run_id)
    summary = UniversalTaskSessionService(store=task_runtime_store, approvals=runtime.approvals).summary(execution.run_id)

    assert any(event.type == "project_analysis_partial" for event in events)
    assert any(event.type == "artifact_creation_started" for event in events)
    assert result is not None
    assert result.outputs["project_analysis_report"]["status"] == "partial"
    assert result.outputs["validation_result"]["status"] in {"passed", "blocked"}
    assert "validation_result" in result.outputs
    assert summary is not None
    assert summary["project_analysis"]["status"] == "partial"
    assert summary["project_analysis"]["partial_readiness"]["safe_to_continue_to_artifact_runtime"] is True
