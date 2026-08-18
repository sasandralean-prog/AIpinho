import pytest

from tests.support.runtime_fixtures import runtime_run
from aipinho.services.runtime.task_run_event_service import TaskRunEventService


def test_event_service_sequences_events(task_runtime_store):
    run = runtime_run()
    task_runtime_store.create_run(run)
    events = TaskRunEventService(task_runtime_store)

    first = events.create(run.run_id, "run_created", "created", "created")
    second = events.create(run.run_id, "run_queued", "queued", "queued")

    assert first.sequence == 1
    assert second.sequence == 2
    assert [event.type for event in events.list(run.run_id)] == ["run_created", "run_queued"]


def test_event_service_rejects_unknown_event_type(task_runtime_store):
    run = runtime_run()
    task_runtime_store.create_run(run)
    events = TaskRunEventService(task_runtime_store)

    with pytest.raises(ValueError):
        events.create(run.run_id, "not_a_runtime_event", "created", "bad")


def test_event_service_sanitizes_metadata(task_runtime_store):
    run = runtime_run()
    task_runtime_store.create_run(run)
    events = TaskRunEventService(task_runtime_store)

    event = events.create(run.run_id, "run_created", "created", "created", metadata={"raw": "secret", "note": "api_key=abc"})

    assert event.metadata["raw"] == "[omitted_by_task_run_store]"
    assert event.metadata["note"] == "[REDACTED]"
