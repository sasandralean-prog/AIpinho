from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from aipinho.schemas.analysis.analysis_report import AnalysisReport
from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.schemas.analysis.project_analysis_result import ProjectAnalysisResult
from aipinho.schemas.analysis.project_tree_summary import ProjectTreeSummary
from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest
from aipinho.schemas.cvl import CognitiveReadinessResult
from aipinho.services.cvl import CognitiveReadinessService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    ReadonlyAnalysisArtifactRuntimeService,
)
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


def _frontier_context() -> dict[str, object]:
    return {
        "predicted_frontier": "PROJECT_ANALYSIS_FILE_READ",
        "predicted_component": "ProjectAnalysisService",
        "predicted_reason_code": "PROJECT_ANALYSIS_FILE_READ_TIMEOUT",
        "predicted_blocking_stage": "after_file_read_item",
        "confidence": 0.84,
        "causal_chain": ["Intent", "Lifecycle", "Workspace", "Contracts", "ProjectAnalysis", "FileRead"],
        "critical_dependencies": ["read_workspace", "analysis_readonly"],
        "alternative_hypotheses": ["PUBLIC_CHAT_RESPONSE_BOUNDARY"],
    }


def _prompt() -> str:
    return (
        "FIRE TEST 5 - FASE 1 - Discovery Governado\n"
        "Esta fase NAO pode modificar nenhum arquivo do projeto.\n"
        "Artifacts obrigatorios\n"
        "reports/firetest5/phase1_discovery.md\n"
        "reports/firetest5/project_inventory.md\n"
        "reports/firetest5/music_inventory.csv\n"
        "reports/firetest5/evidence_phase1.zip\n"
    )


class BlockedProjectAnalysis:
    def analyze_project(self, request: ProjectAnalysisRequest, *, cancel_requested=None) -> ProjectAnalysisResult:
        reason = "PROJECT_ANALYSIS_FILE_READ_TIMEOUT"
        return ProjectAnalysisResult(
            result_id=f"project_analysis_{uuid4().hex}",
            workspace=request.workspace,
            status="timeout",
            tree_summary=ProjectTreeSummary(workspace=request.workspace, status="partial", total_files_seen=8),
            file_context=FileContextBundle(bundle_id=f"file_context_{uuid4().hex}", workspace=request.workspace, status="partial"),
            report=AnalysisReport(
                report_id=f"analysis_report_{uuid4().hex}",
                status="blocked",
                title="Project Analysis Boundary",
                summary="Project analysis timed out during file read.",
            ),
            reason_code=reason,
            error_message="Project analysis budget exceeded during after_file_read_item.",
            safe_to_continue=False,
            budget_exceeded=True,
            duration_ms=20_812,
            last_checkpoint="after_file_read_item",
            last_completed_checkpoint="after_file_read_item",
            files_discovered=7,
            files_scan_attempted=12,
            files_scanned=8,
            files_read=3,
            bytes_read=1234,
            blocking_operation="file_read",
            budget_exceeded_at="after_file_read_item",
            budget={"max_total_seconds": 20.0},
        )


def test_cognitive_readiness_result_enforces_phase0_runtime_invariants(tmp_path: Path) -> None:
    service = CognitiveReadinessService(runtime_reports_root=tmp_path / "runtime", firetest_reports_root=tmp_path / "firetest")
    readiness = service.build_phase0(prompt=_prompt(), frontier_context=_frontier_context())
    payload = readiness.model_dump(mode="json")
    payload["runtime_executed"] = True

    with pytest.raises(ValueError, match="phase0_must_not_create_runtime_state"):
        CognitiveReadinessResult.model_validate(payload)


def test_phase0_generates_canonical_readiness_without_taskrun_or_operation(tmp_path: Path, task_runtime_store) -> None:
    service = CognitiveReadinessService(
        runtime_reports_root=tmp_path / "runtime",
        firetest_reports_root=tmp_path / "firetest",
        store=task_runtime_store,
    )

    readiness = service.build_phase0(prompt=_prompt(), frontier_context=_frontier_context())

    assert readiness.runtime_executed is False
    assert readiness.task_created is False
    assert readiness.task_run_created is False
    assert readiness.operation_created is False
    assert readiness.operational_artifacts_created is False
    assert task_runtime_store.list_runs() == []
    assert readiness.decision.decision == "NO_GO_EXPECTED_BLOCK"
    assert readiness.decision.requires_user_override is True
    assert readiness.prediction.predicted_frontier == "PROJECT_ANALYSIS_FILE_READ"
    assert readiness.prediction.predicted_component == "ProjectAnalysisService"
    assert readiness.prediction.predicted_reason_code == "PROJECT_ANALYSIS_FILE_READ_TIMEOUT"
    assert readiness.dependency_graph.nodes
    assert readiness.coverage_report.coverage_by_domain
    assert readiness.simulation_result.simulated_steps
    assert readiness.simulation_result.simulated_blocking_point == "ProjectAnalysis"
    assert readiness.simulation_result.simulated_reason_code == "PROJECT_ANALYSIS_FILE_READ_TIMEOUT"
    assert readiness.frontier_report.primary_frontier == "PROJECT_ANALYSIS_FILE_READ"
    assert (tmp_path / "runtime" / "firetest5_phase0_cognitive_readiness_result.json").exists()
    assert (tmp_path / "firetest" / "phase0_prediction.md").exists()


def test_phase0_without_frontier_context_does_not_invent_specific_runtime_reason(tmp_path: Path) -> None:
    service = CognitiveReadinessService(runtime_reports_root=tmp_path / "runtime", firetest_reports_root=tmp_path / "firetest")

    readiness = service.build_phase0(prompt=_prompt())

    assert readiness.profile_selection_method == "heuristic_prompt_profile_selection"
    assert readiness.prediction.predicted_reason_code != "PROJECT_ANALYSIS_FILE_READ_TIMEOUT"
    assert readiness.simulation_result.simulated_reason_code != "PROJECT_ANALYSIS_FILE_READ_TIMEOUT"
    assert "FRONTIER_CONTEXT_ATTACHED" not in readiness.profile_selection_reason_codes


def test_phase1_references_phase0_and_calibrates_without_changing_truth(tmp_path: Path, task_runtime_store) -> None:
    readiness_service = CognitiveReadinessService(
        runtime_reports_root=tmp_path / "runtime",
        firetest_reports_root=tmp_path / "firetest",
        store=task_runtime_store,
    )
    readiness = readiness_service.build_phase0(prompt=_prompt(), frontier_context=_frontier_context())
    phase0_ref = str(tmp_path / "runtime" / "firetest5_phase0_cognitive_readiness_result.json")
    runtime = TaskRuntimeService(store=task_runtime_store)
    service = ReadonlyAnalysisArtifactRuntimeService(
        runtime=runtime,
        analysis=BlockedProjectAnalysis(),  # type: ignore[arg-type]
    )

    execution = service.execute(
        request=ChatRequest(
            message=_prompt(),
            session_id="phase0_reference_test",
            context=ChatContext(
                surface="api",
                active_workspace=str(tmp_path),
                cognitive_readiness_id=readiness.readiness_id,
                phase0_result_ref=phase0_ref,
                phase0_prediction_id=readiness.prediction.prediction_id,
                phase0_decision=readiness.decision.decision,
            ),
        ),
        workspace=str(tmp_path),
    )

    run = task_runtime_store.get_run(execution.run_id or "")
    result = task_runtime_store.get_result(execution.run_id or "")
    events = task_runtime_store.get_events(execution.run_id or "")
    summary = UniversalTaskSessionService(store=task_runtime_store, approvals=runtime.approvals).summary(execution.run_id or "")
    calibration_path = tmp_path / "runtime" / "firetest5_phase0_vs_phase1_calibration.json"

    assert run is not None
    assert result is not None
    assert result.status == "blocked"
    assert run.intent_map["cognitive_readiness"]["phase0_result_ref"] == phase0_ref
    assert run.intent_map["cognitive_readiness"]["runtime_executed_despite_cvl_no_go"] is True
    assert any(event.type == "phase0_prediction_attached" for event in events)
    assert any(event.type == "phase0_prediction_calibrated" for event in events)
    assert calibration_path.exists()
    assert summary is not None
    assert summary["cognitive_readiness"]["decision"] == "NO_GO_EXPECTED_BLOCK"
    assert summary["cognitive_readiness"]["runtime_executed_despite_no_go"] is True
    assert summary["cognitive_readiness"]["calibration"]["status"] in {"matched", "partial_match"}
    assert summary["validation"]["status"] == "blocked"
    assert summary["result"]["safe_to_report_success"] is False
