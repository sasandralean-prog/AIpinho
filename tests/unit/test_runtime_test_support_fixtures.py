from __future__ import annotations

from tests.support.runtime_fixtures import one_step_plan, runtime_run


def test_runtime_run_fixture_preserves_canonical_bootstrap_identity() -> None:
    run = runtime_run(contract_type="readonly_analysis", runtime_profile="product_planning_readonly")

    assert run.task_id
    assert run.task_run_id == run.run_id
    assert run.task_id != run.run_id
    assert run.operation_id
    assert run.bootstrap_context["task_id"] == run.task_id
    assert run.bootstrap_context["task_run_id"] == run.run_id
    assert run.bootstrap_context["operation_id"] == run.operation_id
    assert run.bootstrap_context["context"]["requires_task"] is True


def test_one_step_plan_fixture_produces_required_contract_step() -> None:
    plan = one_step_plan(action="read_files", step_type="readonly_analysis")

    assert plan.status == "ready"
    assert len(plan.steps) == 1
    assert plan.steps[0].required is True
    assert plan.steps[0].action == "read_files"
    assert plan.steps[0].step_type == "readonly_analysis"
