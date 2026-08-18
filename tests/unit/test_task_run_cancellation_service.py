from tests.support.runtime_fixtures import runtime_run
from aipinho.services.runtime.task_run_cancellation_service import TaskRunCancellationService
from aipinho.services.runtime.task_run_event_service import TaskRunEventService
from aipinho.services.runtime.task_run_lifecycle_service import TaskRunLifecycleService


def test_cancellation_cancels_created_run(task_runtime_store):
    run = runtime_run()
    task_runtime_store.create_run(run)
    service = TaskRunCancellationService(
        task_runtime_store,
        TaskRunLifecycleService(),
        TaskRunEventService(task_runtime_store),
    )

    result = service.cancel(run.run_id)
    stored = task_runtime_store.get_run(run.run_id)

    assert result.cancellation_requested is True
    assert stored.status == "cancelled"
    assert stored.cancellation_requested is True
    assert "run_cancelled" in [event.type for event in task_runtime_store.get_events(run.run_id)]


def test_cancellation_is_refused_for_terminal_run(task_runtime_store):
    run = runtime_run(status="completed")
    task_runtime_store.create_run(run)
    service = TaskRunCancellationService(
        task_runtime_store,
        TaskRunLifecycleService(),
        TaskRunEventService(task_runtime_store),
    )

    result = service.cancel(run.run_id)

    assert result.cancellation_requested is False
    assert result.message == "terminal_task_run_cannot_be_cancelled"
