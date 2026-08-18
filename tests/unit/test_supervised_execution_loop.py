from tests.support.runtime_fixtures import runtime_context, runtime_run
from aipinho.services.runtime.readonly_task_step_runner import TaskStepOutcome
from aipinho.services.runtime.supervised_execution_loop import SupervisedExecutionLoop
from aipinho.services.runtime.task_run_audit_service import TaskRunAuditService
from aipinho.services.runtime.task_run_event_service import TaskRunEventService
from aipinho.services.runtime.task_run_lifecycle_service import TaskRunLifecycleService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.task_run_guard import TaskRunGuard
from aipinho.schemas.runtime.task_run_step import TaskRunStep


class CompletingExecutor:
    def __init__(self):
        self.calls = 0

    def execute_step(self, run, step, context):
        self.calls += 1
        context.outputs["_role_pipeline"] = {"run_id": "role_pipeline_test", "status": "completed"}
        return TaskStepOutcome(status="completed", summary={"content": "raw should not persist", "safe": "done"})


class PartialExecutor:
    def execute_step(self, run, step, context):
        return TaskStepOutcome(status="partial", summary={"safe": "partial"}, warnings=["budget_reached"], limitations=["budget_reached"])


class OptionalFailureExecutor:
    def execute_step(self, run, step, context):
        if step.step_id == "step_optional":
            return TaskStepOutcome(status="failed", summary={"safe": "failed"}, warnings=["optional_failed"], limitations=["optional_failed"])
        return TaskStepOutcome(status="completed", summary={"safe": "done"})


def build_loop(store, executor):
    lifecycle = TaskRunLifecycleService()
    return SupervisedExecutionLoop(
        store=store,
        lifecycle=lifecycle,
        guard=TaskRunGuard(lifecycle=lifecycle),
        events=TaskRunEventService(store),
        audit=TaskRunAuditService(store),
        executor=executor,
    )


def store_bootstrapped_run(store, run):
    store.create_run(run)
    events = TaskRunEventService(store)
    events.create(
        run.run_id,
        "run_created",
        "created",
        "TaskRun created without execution.",
        metadata={"task_id": run.task_id, "task_run_id": run.run_id, "operation_id": run.operation_id},
    )
    events.create(
        run.run_id,
        "task_bootstrap_created",
        "created",
        "Universal Task identity created before execution.",
        metadata={"task_id": run.task_id, "task_run_id": run.run_id, "operation_id": run.operation_id},
    )


def test_supervised_loop_runs_once_and_is_duplicate_safe(task_runtime_store):
    run = runtime_run()
    store_bootstrapped_run(task_runtime_store, run)
    executor = CompletingExecutor()
    loop = build_loop(task_runtime_store, executor)

    finished, result = loop.run(run.run_id)
    repeated, repeated_result = loop.run(run.run_id)

    assert finished.status == "completed"
    assert result.status == "completed"
    assert repeated.status == "completed"
    assert repeated_result.run_id == result.run_id
    assert executor.calls == 1
    assert "run_completed" in [event.type for event in task_runtime_store.get_events(run.run_id)]


def test_supervised_loop_marks_partial_result(task_runtime_store):
    run = runtime_run()
    store_bootstrapped_run(task_runtime_store, run)
    loop = build_loop(task_runtime_store, PartialExecutor())

    finished, result = loop.run(run.run_id)

    assert finished.status == "partial"
    assert result.status == "partial"
    assert "budget_reached" in result.limitations


def test_supervised_loop_does_not_mark_completed_when_optional_step_leaves_limitation(task_runtime_store):
    run = runtime_run()
    run.plan.steps.append(TaskRunStep(step_id="step_optional", step_type="validate_runtime", action="validate_runtime", required=False))
    store_bootstrapped_run(task_runtime_store, run)
    loop = build_loop(task_runtime_store, OptionalFailureExecutor())

    finished, result = loop.run(run.run_id)

    assert finished.status == "partial"
    assert result.status == "partial"
    assert "optional_failed" in result.limitations


def test_supervised_loop_blocks_when_guard_denies_before_execution(task_runtime_store):
    run = runtime_run(action="write_files")
    store_bootstrapped_run(task_runtime_store, run)
    executor = CompletingExecutor()
    loop = build_loop(task_runtime_store, executor)

    finished, result = loop.run(run.run_id)

    assert finished.status == "blocked"
    assert result.status == "blocked"
    assert executor.calls == 0


def test_supervised_loop_blocks_run_without_initial_timeline_events(task_runtime_store):
    run = runtime_run()
    task_runtime_store.create_run(run)
    executor = CompletingExecutor()
    loop = build_loop(task_runtime_store, executor)

    finished, result = loop.run(run.run_id)

    assert finished.status == "blocked"
    assert result.status == "blocked"
    assert executor.calls == 0
    assert "timeline_events_missing" in finished.blocked_reasons
    assert "run_blocked" in [event.type for event in task_runtime_store.get_events(run.run_id)]
