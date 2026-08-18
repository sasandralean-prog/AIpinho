import pytest

from tests.support.runtime_fixtures import runtime_run
from aipinho.services.runtime.task_run_lifecycle_service import TaskRunLifecycleService


def test_lifecycle_created_to_queued_running_completed():
    lifecycle = TaskRunLifecycleService()
    run = runtime_run()

    lifecycle.transition(run, "queued")
    lifecycle.transition(run, "running")
    lifecycle.transition(run, "completed")

    assert run.status == "completed"
    assert run.started_at is not None
    assert run.finished_at is not None
    assert lifecycle.is_terminal("completed") is True


def test_lifecycle_rejects_invalid_transition():
    lifecycle = TaskRunLifecycleService()
    run = runtime_run()

    with pytest.raises(ValueError):
        lifecycle.transition(run, "completed")


def test_lifecycle_terminal_cannot_cancel():
    lifecycle = TaskRunLifecycleService()

    assert lifecycle.can_cancel("created") is True
    assert lifecycle.can_cancel("completed") is False
