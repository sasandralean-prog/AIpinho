from __future__ import annotations

from datetime import datetime, timezone

from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from tests.support.runtime_fixtures import runtime_run


def test_runtime_budget_terminal_result_has_completion(task_runtime_store) -> None:
    run = runtime_run(status="running").model_copy(
        update={"started_at": "2026-01-01T00:00:00+00:00"}
    )
    task_runtime_store.create_run(run)

    result = task_runtime_store.terminalize_if_runtime_budget_exceeded(
        run.run_id,
        max_runtime_seconds=0,
        reason_code="TASKRUN_LIFECYCLE_TIMEOUT",
    )

    assert result is not None
    assert result.status == "blocked"
    assert result.completion is not None
    assert result.completion.status == "blocked"
    assert result.completion.safe_to_report_success is False


def test_terminal_result_prefers_semantic_artifact_reason_over_stale_timeout(task_runtime_store) -> None:
    artifact = {
        "artifact_id": "artifact_partial_inventory",
        "status": "blocked",
        "reason_code": "MUSIC_INVENTORY_PARTIAL_EVIDENCE",
        "safe_to_use": False,
        "metadata": {
            "semantic_contract_status": "partial",
            "reason_code": "MUSIC_INVENTORY_PARTIAL_EVIDENCE",
            "safe_to_use": False,
        },
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
            event_id="task_run_event_blocked",
            run_id=run.run_id,
            sequence=1,
            type="run_blocked",
            status="blocked",
            message="Run blocked.",
            metadata={"reason_code": "TASKRUN_LIFECYCLE_TIMEOUT"},
        ),
    )

    result = task_runtime_store.ensure_terminal_result(run.run_id)

    assert result is not None
    assert result.validation["reason_code"] == "MUSIC_INVENTORY_PARTIAL_EVIDENCE"
    assert result.completion is not None
    assert result.completion.metadata["reason_code"] == "MUSIC_INVENTORY_PARTIAL_EVIDENCE"
