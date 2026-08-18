from tests.support.runtime_fixtures import runtime_context, runtime_run
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.services.runtime.readonly_task_step_runner import ReadOnlyTaskStepRunner


class HealthyDependency:
    def status(self):
        return {"status": "ok"}


class DisabledDependency:
    def status(self):
        return {"status": "disabled"}


def test_step_runner_blocks_unknown_step_type():
    run = runtime_run()
    context = runtime_context(run)
    step = TaskRunStep(step_id="step_unknown", step_type="unknown", action="validate_runtime")

    outcome = ReadOnlyTaskStepRunner().run(run, step, context)

    assert outcome.status == "blocked"
    assert "unknown_task_step" in outcome.violations


def test_step_runner_validate_runtime_accepts_ok_or_disabled_dependencies():
    run = runtime_run()
    context = runtime_context(run)
    runner = ReadOnlyTaskStepRunner(
        readonly=HealthyDependency(),
        analysis=HealthyDependency(),
        reports=DisabledDependency(),
        roles=HealthyDependency(),
    )

    outcome = runner.run(run, run.plan.steps[0], context)

    assert outcome.status == "completed"
    assert outcome.summary["components"]["reports"] == "disabled"
