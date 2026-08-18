import pytest
from pydantic import ValidationError

from aipinho.app_factory import create_app
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService


def test_task_runtime_routes_are_registered():
    routes = {getattr(route, "path", "") for route in create_app().routes}

    expected = {
        "/api/v1/task-runtime/status",
        "/api/v1/task-runs",
        "/api/v1/task-runs/from-draft/{draft_id}",
        "/api/v1/task-runs/from-preview/{preview_id}",
        "/api/v1/task-runs/{run_id}/start",
        "/api/v1/task-runs/{run_id}/cancel",
        "/api/v1/task-runs/{run_id}/events",
        "/api/v1/task-runs/{run_id}/trace",
        "/api/v1/task-runs/{run_id}/result",
        "/api/v1/task-runtime/queue",
    }
    assert expected.issubset(routes)


def test_task_run_request_rejects_unknown_mode():
    with pytest.raises(ValidationError):
        TaskRunRequest(mode="write")


def test_runtime_status_contract_reports_governed_capabilities(task_runtime_service):
    status = task_runtime_service.status().model_dump()

    assert status["mode"] == "governed_controlled"
    assert status["write_enabled"] is True
    assert status["patch_enabled"] is True
    assert status["shell_enabled"] is True
    assert status["memory_write_enabled"] is False
    assert status["background_execution"] is True


def test_runtime_rejects_actions_not_matching_profile(task_runtime_service):
    for action in ["apply_patch", "run_command"]:
        run = task_runtime_service.create_run(
            TaskRunRequest(
                source_type="direct",
                mode="governed",
                contract_type="in_chat_final_report",
                policy_decision={"status": "allowed", "approval_required_for": []},
                requested_actions=[action],
            )
        )
        assert run.status == "blocked"
        assert f"action_not_allowed_by_profile:{action}" in run.blocked_reasons


def test_runtime_blocks_write_profile_without_approval_even_when_policy_claims_allowed(task_runtime_service):
    registered_workspace = r"C:\Dev\AIpinho\field_trials\rc2\target_mutable_project"
    run = task_runtime_service.create_run(
        TaskRunRequest(
            source_type="direct",
            mode="write_file",
            workspace=registered_workspace,
            contract_type="filesystem_write",
            operation_type="filesystem_write_file",
            policy_decision={
                "status": "allowed",
                "allowed_actions": ["write_files"],
                "approval_required_for": [],
                "safe_to_execute": True,
            },
            requested_actions=["write_files"],
        )
    )

    assert run.status == "blocked"
    assert run.runtime_profile == "write_file"
    assert "write_files" in run.requested_actions
    assert "approval_required" in run.blocked_reasons
    assert "permission_requires_approval:write_files" in run.blocked_reasons
