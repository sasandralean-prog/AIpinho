from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    ReadonlyAnalysisArtifactRuntimeService,
)
from aipinho.services.runtime.task_queue_service import TaskQueueService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from tests.support.runtime_fixtures import runtime_run


TERMINAL_EVENTS = {"run_completed", "run_partial", "run_failed", "run_cancelled", "run_blocked"}


def _media_inventory_started(runtime: TaskRuntimeService, run_id: str) -> TaskRunEvent:
    return runtime.events.create(
        run_id,
        "artifact_creation_started",
        "running",
        "Artifact creation started.",
        metadata={
            "artifact_attempt_id": "artifact_attempt_stage_trace",
            "logical_path": "reports/example_inventory.csv",
            "producer_step": "readonly_analysis_artifact_runtime",
            "artifact_kind": "media_corpus_inventory",
            "contract_id": "media_corpus_inventory_artifact",
        },
    )


def test_post_selection_checkpoint_carries_bounded_artifact_attempt_metadata(task_runtime_store) -> None:
    run = runtime_run(status="running")
    task_runtime_store.create_run(run)
    runtime = TaskRuntimeService(store=task_runtime_store)
    _media_inventory_started(runtime, run.run_id)
    service = ReadonlyAnalysisArtifactRuntimeService(runtime=runtime)
    started = datetime.now(timezone.utc).timestamp()

    service._check_artifact_render_checkpoint(  # noqa: SLF001 - checkpoint contract unit
        run.run_id,
        started,
        started,
        stage="before_perception_payload_compile",
        logical_path="reports/example_inventory.csv",
        rows_rendered=0,
        rows_expected=100,
        cells_rendered=20,
    )

    checkpoint = [event for event in task_runtime_store.get_events(run.run_id) if event.type == "artifact_render_checkpoint"][-1]
    assert checkpoint.metadata["stage"] == "before_perception_payload_compile"
    assert checkpoint.metadata["artifact_attempt_id"] == "artifact_attempt_stage_trace"
    assert checkpoint.metadata["artifact_kind"] == "media_corpus_inventory"
    assert checkpoint.metadata["bounded"] is True
    assert "entities" not in checkpoint.metadata
    assert "rows" not in checkpoint.metadata


def test_stage_specific_stall_reason_wins_after_entity_selection(task_runtime_store) -> None:
    run = runtime_run(status="running")
    task_runtime_store.create_run(run)
    runtime = TaskRuntimeService(store=task_runtime_store)
    started_event = _media_inventory_started(runtime, run.run_id)
    service = ReadonlyAnalysisArtifactRuntimeService(runtime=runtime)
    now = datetime.now(timezone.utc).timestamp()
    service._check_artifact_render_checkpoint(  # noqa: SLF001 - checkpoint contract unit
        run.run_id,
        now,
        now,
        stage="after_entity_selection",
        logical_path="reports/example_inventory.csv",
        rows_rendered=0,
        rows_expected=100,
    )

    result = service._terminalize_accepted_worker_gap(  # noqa: SLF001 - guard contract unit
        run.run_id,
        reason_code="MUSIC_INVENTORY_ARTIFACT_STALLED_AFTER_CREATION_STARTED",
        message="Artifact worker exceeded the artifact terminality budget.",
        artifact_event=started_event,
    )

    assert result is not None
    assert result.validation["reason_code"] == "MUSIC_INVENTORY_PERCEPTION_PAYLOAD_COMPILE_STALLED"
    guard_output = result.outputs["artifact_worker_terminalization_guard"]
    assert guard_output["last_checkpoint_stage"] == "after_entity_selection"
    events = task_runtime_store.get_events(run.run_id)
    assert len([event for event in events if event.type in TERMINAL_EVENTS]) == 1


def test_stage_specific_stall_reason_wins_for_queue_reconcile(task_runtime_store, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_ACCEPTED_WORKER_ARTIFACT_STALL_MS", "10")
    run = runtime_run(status="running")
    task_runtime_store.create_run(run)
    old_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    started = TaskRunEvent(
        event_id=f"task_run_event_{uuid4().hex}",
        run_id=run.run_id,
        sequence=len(task_runtime_store.get_events(run.run_id)) + 1,
        type="artifact_creation_started",
        status="running",
        message="Artifact creation started.",
        timestamp=old_timestamp,
        metadata={
            "artifact_attempt_id": "artifact_attempt_queue_stage_trace",
            "logical_path": "reports/example_inventory.csv",
            "producer_step": "readonly_analysis_artifact_runtime",
            "artifact_kind": "media_corpus_inventory",
            "contract_id": "media_corpus_inventory_artifact",
        },
    )
    task_runtime_store.append_event(run.run_id, started)
    task_runtime_store.append_event(
        run.run_id,
        TaskRunEvent(
            event_id=f"task_run_event_{uuid4().hex}",
            run_id=run.run_id,
            sequence=len(task_runtime_store.get_events(run.run_id)) + 1,
            type="artifact_render_checkpoint",
            status="running",
            message="Artifact render checkpoint reached during before_row_binding.",
            timestamp=old_timestamp,
            metadata={
                "artifact_attempt_id": "artifact_attempt_queue_stage_trace",
                "logical_path": "reports/example_inventory.csv",
                "producer_step": "readonly_analysis_artifact_runtime",
                "stage": "before_row_binding",
                "rows_rendered": 0,
                "rows_expected": 100,
                "bounded": True,
            },
        ),
    )

    result = TaskQueueService(store=task_runtime_store).reconcile()
    persisted = task_runtime_store.get_result(run.run_id)

    assert result.status == "degraded"
    assert persisted is not None
    assert persisted.validation["reason_code"] == "MUSIC_INVENTORY_ROW_BINDING_STALLED"
    guard_output = persisted.outputs["artifact_worker_terminalization_guard"]
    assert guard_output["last_checkpoint_stage"] == "before_row_binding"
    assert len([event for event in task_runtime_store.get_events(run.run_id) if event.type in TERMINAL_EVENTS]) == 1


def test_media_inventory_stall_falls_back_when_internal_stage_unknown(task_runtime_store) -> None:
    run = runtime_run(status="running")
    task_runtime_store.create_run(run)
    runtime = TaskRuntimeService(store=task_runtime_store)
    started_event = _media_inventory_started(runtime, run.run_id)
    service = ReadonlyAnalysisArtifactRuntimeService(runtime=runtime)

    result = service._terminalize_accepted_worker_gap(  # noqa: SLF001 - fallback contract unit
        run.run_id,
        reason_code="ARTIFACT_WORKER_STALLED_AFTER_ARTIFACT_CREATION_STARTED",
        message="Artifact worker exceeded the artifact terminality budget.",
        artifact_event=started_event,
    )

    assert result is not None
    assert result.validation["reason_code"] == "MUSIC_INVENTORY_ARTIFACT_STALLED_AFTER_CREATION_STARTED"


def test_queue_runtime_projection_does_not_call_heavy_reconcile_after_terminal_result(task_runtime_store, monkeypatch) -> None:
    run = runtime_run(status="blocked")
    task_runtime_store.create_run(run)
    runtime = TaskRuntimeService(store=task_runtime_store)

    def fail_reconcile():  # pragma: no cover - only used if regression calls reconcile
        raise AssertionError("queue_status_must_use_lightweight_snapshot")

    monkeypatch.setattr(runtime.queue, "reconcile", fail_reconcile)

    queue = runtime.queue_status()

    assert queue.status == "ok"
    assert queue.snapshot.active_count == 0
    assert queue.snapshot.pending_count == 0
