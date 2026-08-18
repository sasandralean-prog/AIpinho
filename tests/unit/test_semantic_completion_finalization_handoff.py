from __future__ import annotations

from datetime import datetime, timedelta, timezone

from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from aipinho.services.runtime.phase_semantic_completion_policy import PhaseSemanticCompletionPolicy
from aipinho.services.runtime.phase_semantic_result_finalizer import PhaseSemanticResultFinalizer
from tests.support.runtime_fixtures import runtime_run


def _partial_inventory_artifact() -> dict[str, object]:
    return {
        "artifact_id": "artifact_partial_inventory",
        "logical_path": "reports/runtime/media_inventory.csv",
        "status": "blocked",
        "validation_status": "blocked",
        "semantic_contract_status": "partial",
        "reason_code": "MUSIC_INVENTORY_PARTIAL_EVIDENCE",
        "safe_to_use": False,
        "selected_rows": 12,
        "bound_rows": 12,
        "partial_rows": 12,
        "evidence_ref_count": 12,
        "row_evidence_coverage": {"status": "satisfied"},
        "limitations": ["partial_media_corpus_inventory"],
    }


def test_terminal_result_handoff_uses_semantic_reason_not_lifecycle_timeout(task_runtime_store) -> None:
    run = runtime_run(status="blocked").model_copy(
        update={
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "produced_artifacts": [_partial_inventory_artifact()],
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
            message="Run already blocked.",
            metadata={"reason_code": "TASKRUN_LIFECYCLE_TIMEOUT"},
        ),
    )

    result = task_runtime_store.ensure_terminal_result(run.run_id, reason_code="TASKRUN_LIFECYCLE_TIMEOUT")

    assert result is not None
    assert result.source == "phase_semantic_completion_policy"
    assert result.validation["reason_code"] == "MUSIC_INVENTORY_PARTIAL_NOT_ACCEPTED_BY_PHASE_CONTRACT"
    assert result.completion is not None
    assert result.completion.status == "blocked"
    assert result.completion.safe_to_report_success is False
    assert "terminal_result_missing_repaired" not in result.warnings
    assert result.outputs["terminal_result_finalization"]["source"] == "phase_semantic_completion_policy"
    assert result.outputs["terminal_result_finalization"]["store_repair_suppressed_due_to_semantic_artifact_state"] is True


def test_runtime_budget_supervision_suppresses_timeout_when_semantic_artifact_state_exists(task_runtime_store) -> None:
    run = runtime_run(status="running").model_copy(
        update={
            "started_at": (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat(),
            "produced_artifacts": [_partial_inventory_artifact()],
            "blocked_reasons": [],
        }
    )
    task_runtime_store.create_run(run)

    result = task_runtime_store.terminalize_if_runtime_budget_exceeded(
        run.run_id,
        max_runtime_seconds=0,
        reason_code="TASKRUN_LIFECYCLE_TIMEOUT",
    )
    events = task_runtime_store.get_events(run.run_id)

    assert result is not None
    assert result.source == "phase_semantic_completion_policy"
    assert result.validation["reason_code"] == "MUSIC_INVENTORY_PARTIAL_NOT_ACCEPTED_BY_PHASE_CONTRACT"
    assert result.outputs["terminal_result_finalization"]["source"] == "phase_semantic_completion_policy"
    assert [event.type for event in events].count("run_blocked") == 1
    assert task_runtime_store.get_run(run.run_id).blocked_reasons == [
        "MUSIC_INVENTORY_PARTIAL_NOT_ACCEPTED_BY_PHASE_CONTRACT"
    ]


def test_runtime_budget_timeout_still_applies_without_semantic_artifact_state(task_runtime_store) -> None:
    run = runtime_run(status="running").model_copy(
        update={
            "started_at": (datetime.now(timezone.utc) - timedelta(seconds=30)).isoformat(),
            "produced_artifacts": [],
        }
    )
    task_runtime_store.create_run(run)

    result = task_runtime_store.terminalize_if_runtime_budget_exceeded(
        run.run_id,
        max_runtime_seconds=0,
        reason_code="TASKRUN_LIFECYCLE_TIMEOUT",
    )

    assert result is not None
    assert result.source is None
    assert result.validation["reason_code"] == "TASKRUN_LIFECYCLE_TIMEOUT"
    assert result.outputs["runtime_budget"]["reason_code"] == "TASKRUN_LIFECYCLE_TIMEOUT"


def test_semantic_result_finalizer_can_model_limited_completion_without_truth_expansion() -> None:
    run = runtime_run(status="blocked").model_copy(
        update={
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "produced_artifacts": [_partial_inventory_artifact()],
        }
    )
    artifact_state = {
        "status": "partial",
        "count": 1,
        "safe_to_use": False,
        "reason_code": "MUSIC_INVENTORY_PARTIAL_EVIDENCE",
        "partial_or_interrupted": [_partial_inventory_artifact()],
    }
    finalizer = PhaseSemanticResultFinalizer(
        PhaseSemanticCompletionPolicy(partial_inventory_allowed=True)
    )

    result = finalizer.build_result(
        run=run,
        artifacts=[_partial_inventory_artifact()],
        artifact_state=artifact_state,
        events_count=0,
    )

    assert result is not None
    assert result.status == "completed_with_limitations"
    assert result.source == "phase_semantic_completion_policy"
    assert result.completion is not None
    assert result.completion.status == "completed_with_limitations"
    assert "full_inventory" in result.completion.metadata["forbidden_claims"]
