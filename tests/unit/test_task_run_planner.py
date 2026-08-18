from tests.support.runtime_fixtures import runtime_request
from aipinho.services.runtime.task_run_planner import TaskRunPlanner


def test_planner_builds_config_driven_readonly_plan(readonly_workspace):
    plan = TaskRunPlanner().plan(runtime_request(workspace=str(readonly_workspace), contract_type="readonly_analysis"))

    assert plan.status == "ready"
    assert [step.step_type for step in plan.steps][:3] == ["validate_runtime", "validate_workspace", "build_project_tree"]
    assert all(step.side_effect is False for step in plan.steps)


def test_planner_allows_read_files_for_readonly_profile(readonly_workspace):
    plan = TaskRunPlanner().plan(
        runtime_request(
            workspace=str(readonly_workspace),
            contract_type="readonly_analysis",
            operation_type="project_analysis",
            actions=["read_files"],
        )
    )

    assert "action_not_allowed_by_profile:read_files" not in plan.blocked_reasons


def test_planner_blocks_write_action():
    plan = TaskRunPlanner().plan(runtime_request(actions=["write_files"]))

    assert plan.status == "blocked"
    assert "action_not_allowed_by_profile:write_files" in plan.blocked_reasons


def test_planner_allows_governed_write_profile(tmp_path):
    plan = TaskRunPlanner().plan(
        runtime_request(
            workspace=str(tmp_path),
            contract_type="filesystem_write",
            operation_type="filesystem_write_file",
            actions=["write_files"],
            policy={
                "status": "allowed",
                "allowed_actions": ["write_files"],
                "approval_required_for": [],
            },
        )
    )

    assert plan.status == "ready"
    assert plan.metadata["runtime_profile"] == "write_file"
    assert any(step.side_effect for step in plan.steps)


def test_planner_allows_patch_profile_with_report_write_action(tmp_path):
    plan = TaskRunPlanner().plan(
        runtime_request(
            workspace=str(tmp_path),
            contract_type="patch_request",
            operation_type="patch_preview",
            runtime_profile="patch",
            actions=["patch_preview", "apply_patch", "write_files"],
            policy={
                "status": "needs_approval",
                "allowed_actions": ["patch_preview"],
                "approval_required_for": ["apply_patch", "write_files"],
            },
        )
    )

    assert plan.status == "ready"
    assert plan.metadata["runtime_profile"] == "patch"
    assert "action_not_allowed_by_profile:write_files" not in plan.blocked_reasons


def test_planner_blocks_unknown_contract_type():
    plan = TaskRunPlanner().plan(runtime_request(contract_type="unknown_contract"))

    assert plan.status == "blocked"
    assert "unsupported_contract_type" in plan.blocked_reasons
