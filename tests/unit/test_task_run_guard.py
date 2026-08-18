from tests.support.runtime_fixtures import one_step_plan, runtime_run
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.services.runtime.task_run_guard import TaskRunGuard


def test_guard_allows_safe_readonly_run():
    run = runtime_run()
    decision = TaskRunGuard().check_run(run)

    assert decision.allowed is True
    assert decision.status == "allowed"


def test_guard_blocks_run_without_universal_task_bootstrap():
    run = runtime_run()
    run.task_id = None
    run.operation_id = None
    run.task_run_id = None
    run.bootstrap_context = {}

    decision = TaskRunGuard().check_run(run)

    assert decision.allowed is False
    assert "missing_task_id" in decision.blocked_reasons
    assert "missing_task_run_id" in decision.blocked_reasons
    assert "missing_operation_id" in decision.blocked_reasons
    assert "missing_bootstrap_context" in decision.blocked_reasons


def test_guard_blocks_bootstrap_identity_mismatch():
    run = runtime_run()
    run.bootstrap_context["task_id"] = "task_other"

    decision = TaskRunGuard().check_run(run)

    assert decision.allowed is False
    assert "bootstrap_task_id_mismatch" in decision.blocked_reasons


def test_guard_blocks_write_action():
    run = runtime_run(action="write_files")
    decision = TaskRunGuard().check_run(run)

    assert decision.allowed is False
    assert "action_not_allowed_by_profile:write_files" in decision.blocked_reasons


def test_guard_requires_approval_for_governed_write_with_matching_profile():
    registered_workspace = r"C:\Dev\AIpinho\field_trials\rc2\target_mutable_project"
    run = runtime_run(
        action="write_files",
        contract_type="filesystem_write",
        operation_type="filesystem_write_file",
        workspace=registered_workspace,
        policy={
            "status": "allowed",
            "allowed_actions": ["write_files"],
            "denied_actions": [],
            "approval_required_for": [],
        },
    )
    decision = TaskRunGuard().check_run(run)

    assert decision.allowed is False
    assert "approval_required" in decision.blocked_reasons


def test_guard_blocks_side_effect_step():
    run = runtime_run()
    step = TaskRunStep(step_id="step_write", step_type="write", action="write_files", side_effect=True)
    decision = TaskRunGuard().check_step(run, step, step_index=0, elapsed_seconds=0)

    assert decision.allowed is False
    assert "step_not_allowed_by_profile:write" in decision.blocked_reasons
    assert "side_effect_not_allowed_by_profile" in decision.blocked_reasons


def test_guard_blocks_cancelled_run():
    run = runtime_run()
    run.cancellation_requested = True
    decision = TaskRunGuard().check_run(run)

    assert decision.allowed is False
    assert "cancellation_requested" in decision.blocked_reasons


def test_guard_uses_runtime_profile_timeout_for_write_validation():
    run = runtime_run(
        action="write_files",
        contract_type="filesystem_write",
        operation_type="filesystem_write_file",
        runtime_profile="write_file",
        policy={
            "status": "allowed",
            "allowed_actions": ["write_files"],
            "denied_actions": [],
            "approval_required_for": [],
        },
    )
    validation_step = TaskRunStep(
        step_id="step_validate_filesystem_result",
        step_type="validate_filesystem_result",
        action="validate_runtime",
        side_effect=False,
    )

    within_profile_limit = TaskRunGuard().check_step(
        run,
        validation_step,
        step_index=3,
        elapsed_seconds=181,
    )
    over_profile_limit = TaskRunGuard().check_step(
        run,
        validation_step,
        step_index=3,
        elapsed_seconds=601,
    )

    assert within_profile_limit.allowed is True
    assert over_profile_limit.allowed is False
    assert "runtime_timeout_exceeded" in over_profile_limit.blocked_reasons
