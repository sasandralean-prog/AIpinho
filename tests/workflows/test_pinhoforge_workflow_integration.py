from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.main import app
from aipinho.schemas.workflows import WorkflowPlanCreateRequest, WorkflowRunCreateRequest
from aipinho.services.autopilot.workflow_v2_service import WorkflowExecutor, WorkflowPlanner, WorkflowStore


def _env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_WORKFLOW_ROOT", str(tmp_path / "workflows"))
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    monkeypatch.setenv("AIPINHO_LEARNING_ROOT", str(tmp_path / "learning"))
    monkeypatch.setenv("AIPINHO_SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("AIPINHO_SANDBOX_DATA_ROOT", str(tmp_path / "sandbox_data"))


def test_bridge_workflow_plan_selects_provider_steps_from_registry(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)

    plan = WorkflowPlanner().create_plan(
        WorkflowPlanCreateRequest(
            user_goal="Use PinhoForge bridge para consultar readiness e command catalog em modo governado.",
            workflow_type="bridge_provider_workflow",
            requested_capabilities=["pinhoforge_command_catalog_read"],
            metadata_sanitized={"source_scope": "sandbox", "workspace_ref": str(tmp_path)},
        )
    )

    tool_steps = [step for phase in plan.phases for step in phase.steps if step.action_type == "tool_invoke"]
    assert plan.workflow_type == "bridge_provider_workflow"
    assert plan.source_scope == "sandbox"
    assert tool_steps
    assert all((step.provider_id or "").startswith("pinhoforge") for step in tool_steps)
    assert all(step.capability_id for step in tool_steps)
    assert all(step.source_scope != "unknown" for step in tool_steps)
    assert plan.risk_assessment["selected_tools"]


def test_bridge_workflow_executes_readonly_steps_through_tool_gateway(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)

    plan = WorkflowPlanner().create_plan(
        WorkflowPlanCreateRequest(
            user_goal="Rode um workflow PinhoForge read-only para command catalog e readiness.",
            workflow_type="bridge_provider_workflow",
            requested_capabilities=["pinhoforge_command_catalog_read"],
            metadata_sanitized={"source_scope": "sandbox", "workspace_ref": str(tmp_path)},
        )
    )
    run = WorkflowExecutor().create_run(WorkflowRunCreateRequest(workflow_plan_id=plan.workflow_plan_id, autorun=True))
    step_results = WorkflowStore().list_step_results(workflow_run_id=run.workflow_run_id)
    replay = WorkflowStore().list_replays(workflow_run_id=run.workflow_run_id)
    trace = WorkflowExecutor().trace(run.workflow_run_id)

    assert run.status in {"completed", "completed_with_warnings"}
    assert step_results
    assert replay
    assert trace["tool_invocations"]
    assert any("workflow_run:" in ref for item in step_results for ref in item.evidence_refs)
    assert any(item.tool_name == "pinhoforge_command_search" for item in step_results)


def test_bridge_workflow_unknown_source_scope_blocks_before_tool_gateway(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)

    plan = WorkflowPlanner().create_plan(
        WorkflowPlanCreateRequest(
            user_goal="Prepare terminal governado PinhoForge, mas sem source scope autorizado.",
            workflow_type="bridge_provider_workflow",
            metadata_sanitized={
                "source_scope": "unknown",
                "workspace_ref": str(tmp_path),
                "bridge_tools": ["pinhoforge_terminal_preview"],
            },
        )
    )
    run = WorkflowExecutor().create_run(WorkflowRunCreateRequest(workflow_plan_id=plan.workflow_plan_id, autorun=True))
    step_results = WorkflowStore().list_step_results(workflow_run_id=run.workflow_run_id)

    assert run.status == "blocked"
    assert "workflow_step_source_scope_unknown" in run.errors
    blocked_steps = [item for item in step_results if item.status == "blocked"]
    assert blocked_steps
    assert "workflow_step_source_scope_unknown" in blocked_steps[0].errors
    assert blocked_steps[0].source_scope == "unknown"


def test_bridge_workflow_step_results_and_replay_routes(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    client = TestClient(app)
    plan_response = client.post(
        "/api/v1/workflows/plans",
        json={
            "user_goal": "Consulte readiness PinhoForge de forma governada.",
            "workflow_type": "bridge_provider_workflow",
            "requested_capabilities": ["pinhoforge_environment_readiness"],
            "metadata_sanitized": {"source_scope": "sandbox", "workspace_ref": str(tmp_path)},
        },
    )
    assert plan_response.status_code == 200
    plan_id = plan_response.json()["workflow_plan"]["workflow_plan_id"]
    run_response = client.post("/api/v1/workflows/runs", json={"workflow_plan_id": plan_id, "autorun": True})
    assert run_response.status_code == 200
    run_id = run_response.json()["workflow_run"]["workflow_run_id"]

    step_results = client.get(f"/api/v1/workflows/runs/{run_id}/step-results")
    replay = client.get(f"/api/v1/workflows/runs/{run_id}/replay")

    assert step_results.status_code == 200
    assert replay.status_code == 200
    assert step_results.json()["step_results"]
    assert replay.json()["replays"]
