from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from aipinho.services.runtime.task_run_event_service import TaskRunEventService
from aipinho.services.runtime.task_run_store import TaskRunStore


def test_event_sequence_allocation_is_atomic_at_store_boundary(tmp_path) -> None:
    store = TaskRunStore(root=tmp_path / "task_runs")
    events = TaskRunEventService(store)
    run_id = "task_run_" + "a" * 32

    def emit(index: int):
        return events.create(
            run_id,
            "project_analysis_started",
            "running",
            f"event {index}",
        )

    with ThreadPoolExecutor(max_workers=12) as pool:
        created = list(pool.map(emit, range(120)))

    persisted = sorted(store.get_events(run_id), key=lambda item: item.sequence)
    assert len(created) == 120
    assert len(persisted) == 120
    assert [item.sequence for item in persisted] == list(range(1, 121))
    assert len({item.sequence for item in persisted}) == 120
    assert len({item.event_id for item in persisted}) == 120
