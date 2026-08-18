from __future__ import annotations

from pathlib import Path

from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.services.runtime.task_bootstrap_runtime_service import TaskBootstrapRuntimeService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.memory.operational_memory_service import OperationalMemoryService


def _runtime(tmp_path: Path) -> TaskRuntimeService:
    return TaskRuntimeService(
        store=TaskRunStore(root=tmp_path / "task_runs"),
        operational_memory=OperationalMemoryService(root=tmp_path / "memory"),
    )


def _request(
    *,
    workspace: str,
    operation_type: str = "workspace_analysis_readonly",
    runtime_profile: str = "readonly_analysis",
    phase: str | None = None,
    parent_task_id: str | None = None,
    start_immediately: bool = False,
) -> TaskRunRequest:
    intent = {
        "intent_type": operation_type,
        "operation_type": operation_type,
        "phase_id": phase,
        "source_channel": "unit_test",
    }
    return TaskRunRequest(
        source_type="direct",
        session_id="chat_bootstrap",
        source_channel="unit_test",
        workspace=workspace,
        contract_type="readonly_analysis",
        operation_type=operation_type,
        runtime_profile=runtime_profile,
        intent_map={key: value for key, value in intent.items() if value is not None},
        requested_actions=["read_files"],
        policy_decision={
            "status": "allowed",
            "allowed_actions": ["read_files"],
            "approval_required_for": [],
            "denied_actions": [],
        },
        parent_task_id=parent_task_id,
        start_immediately=start_immediately,
        mode="read_only",
    )


def test_readonly_analysis_operation_bootstraps_task_and_taskrun(tmp_path: Path) -> None:
    workspace = tmp_path / "project"
    workspace.mkdir()
    runtime = _runtime(tmp_path)

    run = runtime.create_run(_request(workspace=str(workspace)))

    assert run.task_id and run.task_id.startswith("task_")
    assert run.operation_id and run.operation_id.startswith("op_")
    assert run.task_run_id == run.run_id
    assert run.runtime_profile == "readonly_analysis"
    assert run.workspace == str(workspace)
    assert run.workspace_id and run.workspace_id.startswith("workspace_")
    assert run.project_id and run.project_id.startswith("project_")
    assert run.session_id == "chat_bootstrap"
    assert run.bootstrap_context["task_id"] == run.task_id
    assert runtime.get_events(run.run_id)[0].type == "run_created"
    assert any(event.type == "task_bootstrap_created" for event in runtime.get_events(run.run_id))


def test_planner_executable_bootstraps_without_starting_execution(tmp_path: Path) -> None:
    workspace = tmp_path / "android"
    workspace.mkdir()
    runtime = _runtime(tmp_path)

    run = runtime.create_run(
        _request(
            workspace=str(workspace),
            operation_type="android_project_analysis",
            runtime_profile="readonly_analysis",
            start_immediately=False,
        )
    )

    assert run.task_id
    assert run.task_run_id == run.run_id
    assert run.started_at is None
    assert run.status in {"created", "blocked"}
    assert runtime.get_result(run.run_id) is None


def test_polling_can_locate_bootstrapped_task_by_task_id(tmp_path: Path) -> None:
    workspace = tmp_path / "project"
    workspace.mkdir()
    runtime = _runtime(tmp_path)
    run = runtime.create_run(_request(workspace=str(workspace), phase="phase_1"))

    located = TaskBootstrapRuntimeService(store=runtime.store).lookup(str(run.task_id))
    session = UniversalTaskSessionService(store=runtime.store).get_session(run.run_id)

    assert located is not None
    assert located["task_id"] == run.task_id
    assert located["task_run_id"] == run.run_id
    assert located["runtime"] == run.runtime_profile
    assert located["workspace"] == str(workspace)
    assert located["phase"] == "phase_1"
    assert located["created_at"] == run.created_at
    assert session is not None
    assert session.metadata["task_id"] == run.task_id
    assert session.metadata["operation_id"] == run.operation_id


def test_resume_preserves_bootstrap_context_after_store_reload(tmp_path: Path) -> None:
    workspace = tmp_path / "project"
    workspace.mkdir()
    runtime = _runtime(tmp_path)
    run = runtime.create_run(_request(workspace=str(workspace)))

    reloaded_runtime = TaskRuntimeService(
        store=runtime.store,
        operational_memory=OperationalMemoryService(root=tmp_path / "memory_reload"),
    )
    reloaded = reloaded_runtime.get_run(run.run_id)

    assert reloaded is not None
    assert reloaded.task_id == run.task_id
    assert reloaded.operation_id == run.operation_id
    assert reloaded.workspace_id == run.workspace_id
    assert reloaded.project_id == run.project_id
    assert reloaded.bootstrap_context["task_run_id"] == run.run_id


def test_phase_chain_preserves_workspace_project_parent_and_session(tmp_path: Path) -> None:
    workspace = tmp_path / "project"
    workspace.mkdir()
    runtime = _runtime(tmp_path)

    phase1 = runtime.create_run(_request(workspace=str(workspace), phase="phase_1"))
    phase2 = runtime.create_run(_request(workspace=str(workspace), phase="phase_2", parent_task_id=phase1.task_id))
    phase3 = runtime.create_run(_request(workspace=str(workspace), phase="phase_3", parent_task_id=phase2.task_id))

    assert phase1.current_phase == "phase_1"
    assert phase2.current_phase == "phase_2"
    assert phase3.current_phase == "phase_3"
    assert phase2.parent_task_id == phase1.task_id
    assert phase3.parent_task_id == phase2.task_id
    assert phase1.workspace_id == phase2.workspace_id == phase3.workspace_id
    assert phase1.project_id == phase2.project_id == phase3.project_id
    assert phase1.session_id == phase2.session_id == phase3.session_id == "chat_bootstrap"
