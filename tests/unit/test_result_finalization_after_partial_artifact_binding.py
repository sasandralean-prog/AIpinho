from __future__ import annotations

from datetime import datetime, timezone

from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService
from tests.support.runtime_fixtures import runtime_run


def _partial_music_inventory_artifact() -> dict[str, object]:
    return {
        "artifact_id": "artifact_music_inventory_partial",
        "logical_path": "reports/runtime/music_inventory.csv",
        "status": "blocked",
        "safe_to_use": False,
        "selected_rows": 100,
        "bound_rows": 100,
        "evidence_ref_count": 100,
        "metadata": {
            "logical_path": "reports/runtime/music_inventory.csv",
            "semantic_contract_status": "partial",
            "reason_code": "MUSIC_INVENTORY_PARTIAL_EVIDENCE",
            "safe_to_use": False,
            "row_evidence_coverage": {"status": "satisfied"},
        },
    }


def test_partial_artifact_terminal_run_persists_blocked_result(task_runtime_store) -> None:
    run = runtime_run(status="blocked").model_copy(
        update={
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "produced_artifacts": [_partial_music_inventory_artifact()],
            "blocked_reasons": ["MUSIC_INVENTORY_PARTIAL_EVIDENCE"],
        }
    )
    task_runtime_store.create_run(run)
    task_runtime_store.append_event(
        run.run_id,
        TaskRunEvent(
            event_id="task_run_event_terminal_blocked",
            run_id=run.run_id,
            sequence=1,
            type="run_blocked",
            status="blocked",
            message="Run blocked by semantic artifact partial evidence.",
            metadata={"reason_code": "MUSIC_INVENTORY_PARTIAL_EVIDENCE"},
        ),
    )

    result = task_runtime_store.ensure_terminal_result(run.run_id)
    loaded = task_runtime_store.get_result(run.run_id)
    summary = UniversalTaskSessionService(store=task_runtime_store).summary(run.run_id)

    assert result is not None
    assert loaded is not None
    assert result.status == "blocked"
    assert result.validation["status"] == "blocked"
    assert result.completion is not None
    assert result.completion.status == "blocked"
    assert result.completion.safe_to_report_success is False
    artifact_result = result.outputs["artifact_result"]
    assert artifact_result["artifact_state"]["status"] == "partial"
    assert artifact_result["artifact_state"]["safe_to_use"] is False
    assert artifact_result["artifacts"][0]["bound_rows"] == 100
    assert artifact_result["artifacts"][0]["evidence_ref_count"] == 100
    assert summary is not None
    assert summary["result"]["result_available"] is True
    assert summary["result"]["safe_to_report_success"] is False


def test_terminal_result_finalization_is_idempotent(task_runtime_store) -> None:
    run = runtime_run(status="blocked").model_copy(
        update={
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "produced_artifacts": [_partial_music_inventory_artifact()],
            "blocked_reasons": ["MUSIC_INVENTORY_PARTIAL_EVIDENCE"],
        }
    )
    task_runtime_store.create_run(run)
    task_runtime_store.append_event(
        run.run_id,
        TaskRunEvent(
            event_id="task_run_event_terminal_blocked",
            run_id=run.run_id,
            sequence=1,
            type="run_blocked",
            status="blocked",
            message="Run blocked by semantic artifact partial evidence.",
            metadata={"reason_code": "MUSIC_INVENTORY_PARTIAL_EVIDENCE"},
        ),
    )

    first = task_runtime_store.ensure_terminal_result(run.run_id)
    second = task_runtime_store.ensure_terminal_result(run.run_id)
    events = task_runtime_store.get_events(run.run_id)

    assert first is not None
    assert second is not None
    assert first.model_dump() == second.model_dump()
    assert [event.type for event in events].count("run_blocked") == 1
    assert task_runtime_store.get_result(run.run_id) is not None


def test_terminal_budget_reconciliation_repairs_missing_result_for_blocked_run(task_runtime_store) -> None:
    run = runtime_run(status="blocked").model_copy(
        update={
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "produced_artifacts": [_partial_music_inventory_artifact()],
            "blocked_reasons": ["MUSIC_INVENTORY_PARTIAL_EVIDENCE"],
        }
    )
    task_runtime_store.create_run(run)
    task_runtime_store.append_event(
        run.run_id,
        TaskRunEvent(
            event_id="task_run_event_terminal_blocked",
            run_id=run.run_id,
            sequence=1,
            type="run_blocked",
            status="blocked",
            message="Run blocked by semantic artifact partial evidence.",
            metadata={"reason_code": "MUSIC_INVENTORY_PARTIAL_EVIDENCE"},
        ),
    )

    result = task_runtime_store.terminalize_if_runtime_budget_exceeded(
        run.run_id,
        max_runtime_seconds=0,
        reason_code="PUBLIC_CHAT_RESPONSE_BUDGET_EXCEEDED",
    )
    events = task_runtime_store.get_events(run.run_id)

    assert result is not None
    assert result.status == "blocked"
    assert task_runtime_store.get_result(run.run_id) is not None
    assert [event.type for event in events].count("run_blocked") == 1
    assert [event.type for event in events].count("terminalization_already_applied") == 1


def test_result_endpoint_service_returns_blocked_result_after_partial_artifact(task_runtime_store) -> None:
    run = runtime_run(status="blocked").model_copy(
        update={
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "produced_artifacts": [_partial_music_inventory_artifact()],
            "blocked_reasons": ["MUSIC_INVENTORY_PARTIAL_EVIDENCE"],
        }
    )
    task_runtime_store.create_run(run)

    task_runtime_store.ensure_terminal_result(run.run_id)
    result = TaskRuntimeService(store=task_runtime_store).get_result(run.run_id)

    assert result is not None
    assert result.status == "blocked"
    assert result.validation["reason_code"] == "MUSIC_INVENTORY_PARTIAL_NOT_ACCEPTED_BY_PHASE_CONTRACT"
    assert result.completion is not None
    assert result.completion.safe_to_report_success is False


def test_summary_projection_repairs_missing_terminal_result(task_runtime_store) -> None:
    run = runtime_run(status="blocked").model_copy(
        update={
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "produced_artifacts": [_partial_music_inventory_artifact()],
            "blocked_reasons": ["MUSIC_INVENTORY_PARTIAL_EVIDENCE"],
        }
    )
    task_runtime_store.create_run(run)

    summary = UniversalTaskSessionService(store=task_runtime_store).summary(run.run_id)
    result = task_runtime_store.get_result(run.run_id)

    assert result is not None
    assert result.status == "blocked"
    assert summary is not None
    assert summary["result"]["result_available"] is True
    assert summary["result"]["safe_to_report_success"] is False
