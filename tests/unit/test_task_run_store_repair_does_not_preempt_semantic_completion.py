from __future__ import annotations

from datetime import datetime, timezone

from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from tests.support.runtime_fixtures import runtime_run


def test_store_repair_does_not_overwrite_existing_semantic_result(task_runtime_store) -> None:
    artifact = {
        "artifact_id": "artifact_partial_inventory",
        "logical_path": "reports/runtime/media_inventory.csv",
        "status": "blocked",
        "semantic_contract_status": "partial",
        "reason_code": "MUSIC_INVENTORY_PARTIAL_EVIDENCE",
        "safe_to_use": False,
        "bound_rows": 3,
        "evidence_ref_count": 3,
        "row_evidence_coverage": {"status": "satisfied"},
    }
    run = runtime_run(status="blocked").model_copy(
        update={
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "produced_artifacts": [artifact],
            "blocked_reasons": ["TASKRUN_LIFECYCLE_TIMEOUT"],
        }
    )
    task_runtime_store.create_run(run)
    task_runtime_store.append_event(
        run.run_id,
        TaskRunEvent(
            event_id="task_run_event_terminal",
            run_id=run.run_id,
            sequence=1,
            type="run_blocked",
            status="blocked",
            message="Run blocked once.",
            metadata={"reason_code": "TASKRUN_LIFECYCLE_TIMEOUT"},
        ),
    )

    first = task_runtime_store.ensure_terminal_result(run.run_id, reason_code="TASKRUN_LIFECYCLE_TIMEOUT")
    second = task_runtime_store.ensure_terminal_result(run.run_id, reason_code="TASKRUN_LIFECYCLE_TIMEOUT")
    events = task_runtime_store.get_events(run.run_id)

    assert first is not None
    assert second is not None
    assert first.model_dump() == second.model_dump()
    assert second.source == "phase_semantic_completion_policy"
    assert second.validation["reason_code"] == "MUSIC_INVENTORY_PARTIAL_NOT_ACCEPTED_BY_PHASE_CONTRACT"
    assert [event.type for event in events].count("run_blocked") == 1
