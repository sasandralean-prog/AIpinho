from aipinho.schemas.runtime.execution_plan import (
    CandidatePlan,
    CanonicalExecutionStep,
    CanonicalExecutionPlanSerializer,
)
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.services.runtime.execution_plan_promotion_service import (
    ExecutionPlanPromotionService,
)
from aipinho.services.runtime.governed_task_step_runner import GovernedTaskStepRunner
from tests.support.runtime_fixtures import runtime_run


def test_promotes_candidate_plan_with_policy_snapshot_and_capabilities():
    service = ExecutionPlanPromotionService()
    request = TaskRunRequest(
        task_id="task_test",
        task_run_id="run_test",
        contract_type="readonly_analysis",
        operation_type="repository_analysis",
        workspace="C:/workspace",
        requested_actions=["analyze_workspace"],
        capabilities_required=["reasoning", "reporting"],
        policy_decision={"status": "allowed"},
    )
    task_plan = TaskRunPlan(
        plan_id="plan_test",
        contract_type="readonly_analysis",
        steps=[
            TaskRunStep(
                step_id="step_analyze",
                step_type="analysis",
                action="analyze_workspace",
            )
        ],
        metadata={"required_capabilities": ["reasoning", "reporting"]},
    )

    candidate = service.candidate_from_task_run_plan(
        request=request,
        plan=task_plan,
        workspace_context={"workspace_path": "C:/workspace"},
    )
    decision = service.promote(
        candidate,
        policy_snapshot=request.policy_decision,
        task_id="task_test",
        taskrun_id="run_test",
    )

    assert decision.status == "promoted"
    assert decision.execution_plan is not None
    assert decision.execution_plan.operation_kind == "repository_analysis"
    assert decision.execution_plan.task_id == "task_test"
    assert decision.execution_plan.taskrun_id == "run_test"
    assert decision.execution_plan.required_capabilities == ["reasoning", "reporting"]
    restored = CanonicalExecutionPlanSerializer.from_json(
        CanonicalExecutionPlanSerializer.to_json(decision.execution_plan)
    )
    assert restored.execution_id == decision.execution_plan.execution_id


def test_policy_denial_rejects_candidate_without_mutating_candidate():
    service = ExecutionPlanPromotionService()
    candidate = CandidatePlan(
        semantic_goal="run validation",
        operation_kind="validation",
        requested_actions=["run_tests"],
        targets=["C:/workspace"],
        execution_steps=[
            CanonicalExecutionStep(
                step_id="step_validate",
                step_type="validation",
                action="run_tests",
                side_effect=True,
            )
        ],
        rollback_strategy={"required": True, "strategy": "snapshot"},
    )

    decision = service.promote(
        candidate,
        policy_snapshot={"denied_actions": ["run_tests"]},
    )

    assert decision.status == "rejected"
    assert "action_denied_by_policy:run_tests" in decision.reason_codes
    assert candidate.metadata == {}


def test_side_effect_candidate_requires_targets_and_rollback_strategy():
    service = ExecutionPlanPromotionService()
    candidate = CandidatePlan(
        semantic_goal="apply governed change",
        operation_kind="patch",
        requested_actions=["apply_patch"],
        execution_steps=[
            CanonicalExecutionStep(
                step_id="step_patch",
                step_type="patch",
                action="apply_patch",
                side_effect=True,
            )
        ],
    )

    decision = service.promote(candidate, policy_snapshot={"status": "allowed"})

    assert decision.status == "rejected"
    assert "side_effect_execution_requires_targets" in decision.reason_codes
    assert "side_effect_execution_requires_rollback_strategy" in decision.reason_codes


def test_governed_runner_uses_execution_plan_goal_instead_of_raw_prompt():
    run = runtime_run()
    run.intent_map = {"raw_prompt": "raw prompt must not drive execution"}
    run.plan.canonical_execution_plan.semantic_goal = "canonical execution goal"

    goal = GovernedTaskStepRunner()._execution_goal_for_run(run)

    assert goal == "canonical execution goal"
