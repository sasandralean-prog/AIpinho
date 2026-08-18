from __future__ import annotations

from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_context import TaskRunContext
from aipinho.schemas.runtime.execution_plan import CandidatePlan, CanonicalExecutionPlan, CanonicalExecutionStep
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.runtime.task_run_step import TaskRunStep


def allowed_policy(**extra: object) -> dict[str, object]:
    policy = {
        "status": "allowed",
        "contract_type": "in_chat_final_report",
        "allowed_actions": [],
        "denied_actions": [],
        "approval_required_for": [],
        "safe_to_preview": True,
        "safe_to_execute": True,
    }
    policy.update(extra)
    return policy


def runtime_request(
    *,
    workspace: str | None = None,
    contract_type: str = "in_chat_final_report",
    operation_type: str | None = None,
    runtime_profile: str | None = None,
    mode: str = "governed",
    actions: list[str] | None = None,
    policy: dict[str, object] | None = None,
    approval_id: str | None = None,
    start_immediately: bool = False,
) -> TaskRunRequest:
    return TaskRunRequest(
        source_type="direct",
        mode=mode,
        session_id="session_test",
        workspace=workspace,
        contract_type=contract_type,
        operation_type=operation_type,
        runtime_profile=runtime_profile,
        intent_map={"intent_type": contract_type},
        policy_decision=policy if policy is not None else allowed_policy(contract_type=contract_type),
        approval_id=approval_id,
        requested_actions=list(actions or []),
        start_immediately=start_immediately,
    )


def one_step_plan(action: str = "validate_runtime", step_type: str = "validate_runtime") -> TaskRunPlan:
    canonical_step = CanonicalExecutionStep(
        step_id="step_01",
        step_type=step_type,
        action=action,
        required=True,
        side_effect=action in {"write_files", "apply_patch", "run_command", "run_tests"},
    )
    candidate = CandidatePlan(
        semantic_goal="test_runtime_fixture",
        operation_kind=step_type,
        requested_actions=[] if action == "validate_runtime" else [action],
        execution_steps=[canonical_step],
    )
    execution = CanonicalExecutionPlan(
        candidate_plan_id=candidate.candidate_plan_id,
        task_id="task_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        taskrun_id="task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        semantic_goal=candidate.semantic_goal,
        operation_kind=step_type,
        policy_snapshot=allowed_policy(),
        approval_required=canonical_step.side_effect,
        execution_steps=[canonical_step],
        rollback_strategy={"required": canonical_step.side_effect},
        trace_id=candidate.trace_id,
        targets=["fixture_target"] if canonical_step.side_effect else [],
    )
    return TaskRunPlan(
        plan_id="task_run_plan_test",
        contract_type="in_chat_final_report",
        status="ready",
        steps=[TaskRunStep(step_id="step_01", step_type=step_type, action=action, required=True)],
        candidate_plan=candidate,
        canonical_execution_plan=execution,
        metadata={"execution_id": execution.execution_id},
    )


def runtime_run(
    *,
    status: str = "created",
    policy: dict[str, object] | None = None,
    action: str = "validate_runtime",
    contract_type: str = "in_chat_final_report",
    operation_type: str | None = None,
    runtime_profile: str | None = None,
    workspace: str | None = None,
) -> TaskRun:
    run_id = "task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    task_id = "task_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    operation_id = "op_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    return TaskRun(
        run_id=run_id,
        task_id=task_id,
        operation_id=operation_id,
        task_run_id=run_id,
        bootstrap_context={
            "task_id": task_id,
            "operation_id": operation_id,
            "task_run_id": run_id,
            "runtime_profile": runtime_profile or contract_type,
            "workspace": workspace,
            "operation_type": operation_type,
            "contract_type": contract_type,
            "context": {
                "requires_task": True,
                "bootstrap_invariant": "execution_requires_universal_task",
            },
        },
        source_type="direct",
        session_id="session_test",
        workspace=workspace,
        contract_type=contract_type,
        operation_type=operation_type,
        runtime_profile=runtime_profile,
        requested_actions=[] if action == "validate_runtime" else [action],
        policy_snapshot=policy or allowed_policy(contract_type=contract_type),
        plan=one_step_plan(action=action),
        status=status,
    )


def runtime_context(run: TaskRun) -> TaskRunContext:
    return TaskRunContext(run_id=run.run_id, workspace=run.workspace)
