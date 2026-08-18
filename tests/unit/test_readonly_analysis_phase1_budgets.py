from __future__ import annotations

import time
import json
from uuid import uuid4

import pytest

from aipinho.core.paths import PATHS
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    GovernedPhase1Block,
    Phase1RuntimeBudget,
    ReadonlyAnalysisArtifactRuntimeService,
)
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from tests.support.runtime_fixtures import runtime_run


def test_phase1_budget_checkpoint_blocks_expired_runtime(task_runtime_store):
    run = runtime_run(status="running")
    task_runtime_store.create_run(run)
    service = ReadonlyAnalysisArtifactRuntimeService(
        runtime=TaskRuntimeService(store=task_runtime_store),
        budget=Phase1RuntimeBudget(max_runtime_seconds=0.001),
    )

    with pytest.raises(GovernedPhase1Block) as exc:
        service._check_phase1_budget(run.run_id, time.monotonic() - 10, stage="diagnostic")

    assert exc.value.reason_code == "PHASE1_RUNTIME_BUDGET_EXCEEDED"
    assert exc.value.details["terminal_reason"] == "TASKRUN_LIFECYCLE_TIMEOUT"


def test_phase1_cancel_checkpoint_is_cooperative(task_runtime_store):
    run = runtime_run(status="running")
    run.cancellation_requested = True
    run.cancellation_reason = "operator_requested"
    task_runtime_store.create_run(run)
    service = ReadonlyAnalysisArtifactRuntimeService(runtime=TaskRuntimeService(store=task_runtime_store))

    with pytest.raises(GovernedPhase1Block) as exc:
        service._check_phase1_budget(run.run_id, time.monotonic(), stage="artifact_render")

    assert exc.value.status == "cancelled"
    assert exc.value.reason_code == "CANCEL_CHECKPOINT_REACHED"
    assert exc.value.details["cooperative_cancel_checkpoint_seen"] is True


def test_csv_cell_rendering_spills_large_metadata_with_ref():
    service = ReadonlyAnalysisArtifactRuntimeService(
        budget=Phase1RuntimeBudget(max_csv_cell_bytes=80),
    )
    task_run_id = f"task_run_render_{uuid4().hex}"

    cell = service._render_csv_cell(
        {"album": "x" * 500, "track": 1},
        canonical_key="metadata",
        task_run_id=task_run_id,
    )
    payload = json.loads(cell)

    assert payload["reason_code"] == "CSV_FIELD_SPILLED_TO_REF"
    assert payload["canonical_key"] == "metadata"
    assert payload["hash"]
    assert payload["content_ref"]
    assert (PATHS.project_root / payload["content_ref"]).exists()


def test_artifact_render_checkpoint_rejects_late_artifact_after_terminal(task_runtime_store):
    run = runtime_run(status="running")
    task_runtime_store.create_run(run)
    runtime = TaskRuntimeService(store=task_runtime_store)
    runtime.events.create(run.run_id, "run_blocked", "blocked", "already terminal", metadata={"reason_code": "TASKRUN_LIFECYCLE_TIMEOUT"})
    service = ReadonlyAnalysisArtifactRuntimeService(runtime=runtime)

    with pytest.raises(GovernedPhase1Block) as exc:
        service._check_artifact_render_checkpoint(
            run.run_id,
            time.monotonic(),
            time.monotonic(),
            stage="before_registry_create",
            logical_path="reports/firetest5/music_inventory.csv",
        )

    events = task_runtime_store.get_events(run.run_id)
    assert exc.value.reason_code == "ARTIFACT_RENDER_LATE_ARTIFACT_REJECTED"
    assert [event.type for event in events].count("run_blocked") == 1
    assert events[-1].type == "artifact_late_rejected"
    assert events[-1].metadata["safe_to_use"] is False


def test_artifact_render_checkpoint_blocks_column_budget(task_runtime_store):
    run = runtime_run(status="running")
    task_runtime_store.create_run(run)
    service = ReadonlyAnalysisArtifactRuntimeService(
        runtime=TaskRuntimeService(store=task_runtime_store),
        budget=Phase1RuntimeBudget(max_artifact_columns=2),
    )

    with pytest.raises(GovernedPhase1Block) as exc:
        service._contract_tabular_collection_content(
            expected_schema=["name", "codec", "duration"],
            analysis_payload={"observed_entity_graph": {"entities": [], "semantic_gaps": []}},
            declared_contract={"task_run_id": run.run_id, "artifact_logical_path": "reports/firetest5/music_inventory.csv"},
            run_id=run.run_id,
            phase_started_monotonic=time.monotonic(),
            artifact_started_monotonic=time.monotonic(),
        )

    assert exc.value.reason_code == "ARTIFACT_RENDER_OUTPUT_BUDGET_EXCEEDED"
    assert exc.value.details["stage"] == "before_csv_row_write"
