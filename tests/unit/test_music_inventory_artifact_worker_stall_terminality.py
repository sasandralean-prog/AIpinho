from __future__ import annotations

import time
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    AcceptedRunningWorkerTerminalityPolicy,
    GovernedPhase1Block,
    ReadonlyAnalysisArtifactRuntimeService,
)
from aipinho.services.runtime.task_queue_service import TaskQueueService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from tests.support.runtime_fixtures import runtime_run


TERMINAL_EVENTS = {"run_completed", "run_partial", "run_failed", "run_cancelled", "run_blocked"}


def _service(runtime: TaskRuntimeService) -> ReadonlyAnalysisArtifactRuntimeService:
    return ReadonlyAnalysisArtifactRuntimeService(
        runtime=runtime,
        accepted_worker_terminality_policy=AcceptedRunningWorkerTerminalityPolicy(
            poll_interval_ms=5,
            max_artifact_silence_ms=10,
            max_worker_exit_grace_ms=1,
        ),
    )


def test_media_inventory_artifact_stall_gets_semantic_terminal_reason(task_runtime_store) -> None:
    run = runtime_run(
        status="running",
        contract_type="analysis_readonly",
        operation_type="workspace_analysis_readonly",
        runtime_profile="readonly_analysis_artifact_runtime",
    )
    task_runtime_store.create_run(run)
    runtime = TaskRuntimeService(store=task_runtime_store)
    service = _service(runtime)
    started = runtime.events.create(
        run.run_id,
        "artifact_creation_started",
        "running",
        "Artifact creation started.",
        metadata={
            "logical_path": "reports/example_inventory.csv",
            "producer_step": "readonly_analysis_artifact_runtime",
            "artifact_kind": "media_corpus_inventory",
            "contract_id": "media_corpus_inventory_artifact",
        },
    )

    result = service._terminalize_accepted_worker_gap(  # noqa: SLF001 - guard contract unit
        run.run_id,
        reason_code="ARTIFACT_WORKER_STALLED_AFTER_ARTIFACT_CREATION_STARTED",
        message="Artifact worker exceeded the artifact terminality budget.",
        artifact_event=started,
    )

    assert result is not None
    assert result.status == "blocked"
    assert result.source == "artifact_worker_terminalization_guard"
    assert result.validation["reason_code"] == "MUSIC_INVENTORY_ARTIFACT_STALLED_AFTER_CREATION_STARTED"
    assert result.completion is not None
    assert result.completion.safe_to_report_success is False
    events = task_runtime_store.get_events(run.run_id)
    assert len([event for event in events if event.type in TERMINAL_EVENTS]) == 1
    assert any(
        event.type == "artifact_failed"
        and (event.metadata or {}).get("reason_code") == "MUSIC_INVENTORY_ARTIFACT_STALLED_AFTER_CREATION_STARTED"
        for event in events
    )


def test_queue_reconcile_preserves_media_inventory_stall_reason(task_runtime_store, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_ACCEPTED_WORKER_ARTIFACT_STALL_MS", "10")
    run = runtime_run(
        status="running",
        contract_type="analysis_readonly",
        operation_type="workspace_analysis_readonly",
        runtime_profile="readonly_analysis_artifact_runtime",
    )
    task_runtime_store.create_run(run)
    old_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    task_runtime_store.append_event(
        run.run_id,
        TaskRunEvent(
            event_id=f"task_run_event_{uuid4().hex}",
            run_id=run.run_id,
            sequence=len(task_runtime_store.get_events(run.run_id)) + 1,
            type="artifact_creation_started",
            status="running",
            message="Artifact creation started.",
            timestamp=old_timestamp,
            metadata={
                "logical_path": "reports/example_inventory.csv",
                "producer_step": "readonly_analysis_artifact_runtime",
                "artifact_kind": "media_corpus_inventory",
                "contract_id": "media_corpus_inventory_artifact",
            },
        ),
    )

    result = TaskQueueService(store=task_runtime_store).reconcile()
    persisted = task_runtime_store.get_result(run.run_id)
    events = task_runtime_store.get_events(run.run_id)

    assert result.status == "degraded"
    assert persisted is not None
    assert persisted.validation["reason_code"] == "MUSIC_INVENTORY_ARTIFACT_STALLED_AFTER_CREATION_STARTED"
    assert len([event for event in events if event.type in TERMINAL_EVENTS]) == 1


def test_artifact_render_checkpoint_event_is_bounded(task_runtime_store) -> None:
    run = runtime_run(status="running")
    task_runtime_store.create_run(run)
    runtime = TaskRuntimeService(store=task_runtime_store)
    service = ReadonlyAnalysisArtifactRuntimeService(runtime=runtime)
    started = time.monotonic()

    service._check_artifact_render_checkpoint(  # noqa: SLF001 - checkpoint contract unit
        run.run_id,
        started,
        started,
        stage="after_entity_selection",
        logical_path="reports/example_inventory.csv",
        rows_rendered=0,
        rows_expected=100,
    )
    service._check_artifact_render_checkpoint(  # noqa: SLF001 - checkpoint contract unit
        run.run_id,
        started,
        started,
        stage="after_entity_selection",
        logical_path="reports/example_inventory.csv",
        rows_rendered=0,
        rows_expected=100,
    )

    checkpoints = [event for event in task_runtime_store.get_events(run.run_id) if event.type == "artifact_render_checkpoint"]
    assert len(checkpoints) == 1
    assert checkpoints[0].metadata["stage"] == "after_entity_selection"
    assert checkpoints[0].metadata["bounded"] is True


def test_post_commit_checkpoint_does_not_retroactively_timeout_artifact(task_runtime_store) -> None:
    run = runtime_run(status="running")
    task_runtime_store.create_run(run)
    runtime = TaskRuntimeService(store=task_runtime_store)
    service = ReadonlyAnalysisArtifactRuntimeService(runtime=runtime)
    service.budget = replace(service.budget, max_artifact_render_seconds=0.001)
    old_started = time.monotonic() - 1

    with pytest.raises(GovernedPhase1Block) as timeout:
        service._check_artifact_render_checkpoint(  # noqa: SLF001 - checkpoint contract unit
            run.run_id,
            old_started,
            old_started,
            stage="before_artifact_commit",
            logical_path="reports/example_inventory.csv",
        )

    assert timeout.value.reason_code == "ARTIFACT_PERSIST_COMMIT_STALLED"

    service._check_artifact_render_checkpoint(  # noqa: SLF001 - checkpoint contract unit
        run.run_id,
        old_started,
        old_started,
        stage="after_artifact_persist",
        logical_path="reports/example_inventory.csv",
    )

    stages = [
        (event.metadata or {}).get("stage")
        for event in task_runtime_store.get_events(run.run_id)
        if event.type == "artifact_render_checkpoint"
    ]
    assert "after_artifact_persist" in stages


def test_known_render_stage_timeout_uses_stage_specific_reason(task_runtime_store) -> None:
    run = runtime_run(status="running")
    task_runtime_store.create_run(run)
    runtime = TaskRuntimeService(store=task_runtime_store)
    service = ReadonlyAnalysisArtifactRuntimeService(runtime=runtime)
    service.budget = replace(service.budget, max_artifact_render_seconds=0.001)
    old_started = time.monotonic() - 1

    with pytest.raises(GovernedPhase1Block) as timeout:
        service._check_artifact_render_checkpoint(  # noqa: SLF001 - checkpoint contract unit
            run.run_id,
            old_started,
            old_started,
            stage="before_csv_cell_render",
            logical_path="reports/example_inventory.csv",
            rows_rendered=10,
            cells_rendered=100,
        )

    assert timeout.value.reason_code == "MUSIC_INVENTORY_CSV_STREAMING_BUDGET_EXCEEDED"


def test_lightweight_run_projection_does_not_hydrate_spilled_artifacts(task_runtime_store) -> None:
    run = runtime_run(status="running")
    run.produced_artifacts = [
        {"logical_path": f"reports/artifact_{index}.md", "status": "ready", "metadata": {"sample": "x" * 2000}}
        for index in range(160)
    ]
    task_runtime_store.create_run(run)

    lightweight = task_runtime_store.get_run_lightweight(run.run_id)
    full = task_runtime_store.get_run(run.run_id)
    run_json_bytes = (task_runtime_store.root / run.run_id / "run.json").stat().st_size

    assert lightweight is not None
    assert lightweight.produced_artifacts == []
    assert full is not None
    assert len(full.produced_artifacts) == 160
    assert run_json_bytes < 250_000
