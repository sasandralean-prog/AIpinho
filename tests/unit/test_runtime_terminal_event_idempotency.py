from __future__ import annotations

from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from tests.support.runtime_fixtures import runtime_run


def _event(event_type: str, sequence: int, *, reason_code: str) -> TaskRunEvent:
    return TaskRunEvent(
        event_id=f"task_run_event_{sequence}",
        run_id="task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        sequence=sequence,
        type=event_type,
        status="blocked" if event_type == "run_blocked" else "completed",
        message=event_type,
        metadata={"reason_code": reason_code},
    )


def test_append_event_deduplicates_terminal_events_at_store_boundary(task_runtime_store) -> None:
    run = runtime_run(status="running")
    task_runtime_store.create_run(run)

    first = task_runtime_store.append_event(run.run_id, _event("run_blocked", 1, reason_code="FIRST_BLOCK"))
    second = task_runtime_store.append_event(run.run_id, _event("run_blocked", 2, reason_code="SECOND_BLOCK"))
    events = task_runtime_store.get_events(run.run_id)

    assert first.type == "run_blocked"
    assert second.type == "terminalization_already_applied"
    assert [event.type for event in events].count("run_blocked") == 1
    assert [event.type for event in events].count("terminalization_already_applied") == 1
    assert events[-1].metadata["attempted_reason_code"] == "SECOND_BLOCK"


def test_append_event_allows_non_terminal_artifact_state_after_terminal(task_runtime_store) -> None:
    run = runtime_run(status="running")
    task_runtime_store.create_run(run)
    task_runtime_store.append_event(run.run_id, _event("run_blocked", 1, reason_code="FIRST_BLOCK"))

    artifact_event = TaskRunEvent(
        event_id="task_run_event_artifact_blocked",
        run_id=run.run_id,
        sequence=2,
        type="artifact_blocked",
        status="blocked",
        message="Artifact blocked after semantic validation.",
        metadata={"reason_code": "ARTIFACT_SEMANTIC_CONTRACT_BLOCKED"},
    )
    stored = task_runtime_store.append_event(run.run_id, artifact_event)

    assert stored.type == "artifact_blocked"
    assert [event.type for event in task_runtime_store.get_events(run.run_id)].count("run_blocked") == 1
