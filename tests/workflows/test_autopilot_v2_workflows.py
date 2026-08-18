from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.main import app
from aipinho.schemas.workflows import WorkflowCancelRequest, WorkflowPlanCreateRequest, WorkflowResumeRequest, WorkflowRunCreateRequest
from aipinho.services.autopilot.workflow_v2_service import WorkflowExecutor, WorkflowPlanner, WorkflowStore


def _env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_WORKFLOW_ROOT", str(tmp_path / "workflows"))
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    monkeypatch.setenv("AIPINHO_LEARNING_ROOT", str(tmp_path / "learning"))
    monkeypatch.setenv("AIPINHO_SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("AIPINHO_SANDBOX_DATA_ROOT", str(tmp_path / "sandbox_data"))


def test_workflow_plan_has_phases_checkpoints_strategy_and_skill_pack(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    goal = Path("tests/fixtures/workflows/sandbox_creation_goal.txt").read_text(encoding="utf-8")

    plan = WorkflowPlanner().create_plan(WorkflowPlanCreateRequest(user_goal=goal))

    assert plan.workflow_type == "sandbox_creation"
    assert [phase.name for phase in plan.phases]
    assert "event_trace_exists" in plan.validation_strategy
    assert "resume_from_checkpoint" in plan.recovery_strategy
    assert plan.expected_memory_candidates
    assert plan.selected_skill_packs
    assert plan.workspace_context.sandbox_workspace_id


def test_external_workspace_plan_blocks_for_onboarding_without_execution(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    goal = Path("tests/fixtures/workflows/external_workspace_goal.txt").read_text(encoding="utf-8")

    plan = WorkflowPlanner().create_plan(WorkflowPlanCreateRequest(user_goal=goal))
    run = WorkflowExecutor().create_run(WorkflowRunCreateRequest(workflow_plan_id=plan.workflow_plan_id, autorun=True))

    assert plan.workflow_type == "external_workspace_onboarding"
    assert plan.workspace_context.onboarding_required is True
    assert run.status == "blocked"
    assert "external_workspace_onboarding_required" in run.warnings
    assert WorkflowStore().list_recoveries(workflow_run_id=run.workflow_run_id)


def test_medium_risk_workflow_requires_approval_then_completes_with_report(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    fixture = json.loads(Path("tests/fixtures/workflows/approval_required_workflow.json").read_text(encoding="utf-8"))
    plan = WorkflowPlanner().create_plan(WorkflowPlanCreateRequest(**fixture))

    run = WorkflowExecutor().create_run(WorkflowRunCreateRequest(workflow_plan_id=plan.workflow_plan_id, autorun=True))

    assert run.status == "waiting_for_approval"
    approvals = WorkflowStore().list_approvals(workflow_run_id=run.workflow_run_id, status="pending")
    assert approvals

    approved = WorkflowExecutor().approve(run.workflow_run_id, approvals[0].approval_id)

    assert approved.status in {"completed", "completed_with_warnings"}
    assert approved.artifact_ids
    assert approved.checkpoint_ids
    assert approved.validation_ids
    assert WorkflowStore().list_reports()


def test_pause_resume_cancel_and_recovery_are_traceable(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    plan = WorkflowPlanner().create_plan(
        WorkflowPlanCreateRequest(
            user_goal="Analise um projeto conhecido, gere relatorio e preserve checkpoints.",
            workflow_type="project_analysis",
        )
    )
    run = WorkflowExecutor().create_run(WorkflowRunCreateRequest(workflow_plan_id=plan.workflow_plan_id, autorun=False))
    run = WorkflowExecutor().execute(run.workflow_run_id)
    assert run.status in {"completed", "completed_with_warnings"}

    recovery = WorkflowExecutor().recover(run.workflow_run_id)
    cancelled = WorkflowExecutor().cancel(run.workflow_run_id, WorkflowCancelRequest(reason="cleanup_test"))
    trace = WorkflowExecutor().trace(run.workflow_run_id)

    assert recovery.recovery_plan_id in cancelled.recovery_plan_ids
    assert cancelled.status == "cancelled"
    assert trace["checkpoints"]
    assert trace["reports"]


def test_mobile_workflow_view_model_and_http_routes(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    client = TestClient(app)

    plan_response = client.post(
        "/api/v1/workflows/plans",
        json={"user_goal": "Crie um site estatico em sandbox e gere artifact zip."},
    )
    assert plan_response.status_code == 200
    plan_id = plan_response.json()["workflow_plan"]["workflow_plan_id"]

    run_response = client.post("/api/v1/workflows/runs", json={"workflow_plan_id": plan_id, "autorun": False})
    assert run_response.status_code == 200
    run_id = run_response.json()["workflow_run"]["workflow_run_id"]

    trace_response = client.get(f"/api/v1/workflows/runs/{run_id}/trace")
    mobile_response = client.get("/api/v1/mobile/view-model/workflows")

    assert trace_response.status_code == 200
    assert mobile_response.status_code == 200
    assert mobile_response.json()["state"]["raw_default_visible"] is False


def test_resume_request_schema_is_supported_by_service(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    plan = WorkflowPlanner().create_plan(WorkflowPlanCreateRequest(user_goal="Planeje uma analise longa com checkpoints.", workflow_type="project_analysis"))
    run = WorkflowExecutor().create_run(WorkflowRunCreateRequest(workflow_plan_id=plan.workflow_plan_id, autorun=False))
    running = WorkflowExecutor().execute(run.workflow_run_id)
    assert running.status in {"completed", "completed_with_warnings"}

    request = WorkflowResumeRequest(**json.loads(Path("tests/fixtures/workflows/resume_from_checkpoint.json").read_text(encoding="utf-8")))

    assert request.reason.startswith("Retomar")
