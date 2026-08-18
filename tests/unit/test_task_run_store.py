import pytest
import json
import time
from datetime import datetime, timedelta, timezone

from tests.support.runtime_fixtures import runtime_request, runtime_run
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from aipinho.schemas.runtime.workspace_context import ExecutionContext
from aipinho.services.runtime.runtime_storage_compaction_service import RuntimeStorageCompactionService
from aipinho.services.runtime.task_queue_service import TaskQueueService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.runtime.task_run_store import TaskRunStore


def test_store_persists_run_events_result_and_trace(task_runtime_store):
    run = runtime_run()
    task_runtime_store.create_run(run)
    loaded = task_runtime_store.get_run(run.run_id)

    assert loaded is not None
    assert loaded.run_id == run.run_id
    assert task_runtime_store.get_events(run.run_id) == []
    assert task_runtime_store.get_result(run.run_id) is None
    assert task_runtime_store.get_trace(run.run_id) == []
    assert (task_runtime_store.root / run.run_id / "run_index.json").exists()


def test_store_rejects_invalid_run_id(task_runtime_store):
    with pytest.raises(ValueError):
        task_runtime_store.get_run("../escape")


def test_store_sanitizes_raw_content_and_secrets(task_runtime_store):
    value = task_runtime_store.sanitize({"content": "full raw", "safe": "token=abc123 value"})

    assert value["content"] == "[omitted_by_task_run_store]"
    assert value["safe"].startswith("[REDACTED]")


def test_store_custom_root_is_self_confined(tmp_path):
    store = TaskRunStore(root=tmp_path / "isolated")
    run = runtime_run()

    store.create_run(run)

    assert (tmp_path / "isolated" / run.run_id / "run.json").exists()


def test_store_spills_large_runtime_payloads_to_refs(tmp_path):
    store = TaskRunStore(root=tmp_path / "runs")
    run = runtime_run()
    store.create_run(run)
    result = TaskRunResult(
        run_id=run.run_id,
        status="blocked",
        summary="blocked",
        outputs={
            "artifact_result": {
                "artifacts": [
                    {
                        "artifact_id": f"artifact_{index}",
                        "logical_path": "reports/entities.csv",
                        "metadata": {
                            "declared_contract": {
                                "perception": {
                                    "attribute_observations": [{"canonical_key": "codec"}] * 20
                                }
                            }
                        },
                    }
                    for index in range(130)
                ]
            }
        },
    )

    store.save_result(run.run_id, result)
    raw = (tmp_path / "runs" / run.run_id / "result.json").read_text(encoding="utf-8")
    loaded = store.get_result(run.run_id)

    assert "RUNTIME_PAYLOAD_SPILLED_TO_REF" in raw
    assert (tmp_path / "runs" / run.run_id / "payload_refs").exists()
    assert loaded is not None
    artifacts = loaded.outputs["artifact_result"]["artifacts"]
    assert artifacts["content_ref"]
    assert artifacts["record_count"] == 130


def test_store_hydrates_spilled_execution_context_before_task_run_validation(tmp_path):
    store = TaskRunStore(root=tmp_path / "runs")
    run = runtime_run().model_copy(
        update={
            "execution_context": ExecutionContext(
                artifacts=[
                    {
                        "artifact_id": f"artifact_{index}",
                        "logical_path": "reports/entities.csv",
                        "evidence": "x" * 4000,
                    }
                    for index in range(130)
                ]
            )
        }
    )

    store.create_run(run)
    raw = json.loads((tmp_path / "runs" / run.run_id / "run.json").read_text(encoding="utf-8"))
    loaded = store.get_run(run.run_id)

    assert raw["execution_context"]["artifacts"]["reason_code"] == "RUNTIME_PAYLOAD_SPILLED_TO_REF"
    assert loaded is not None
    assert loaded.execution_context is not None
    assert isinstance(loaded.execution_context.artifacts, list)
    assert len(loaded.execution_context.artifacts) == 130
    assert loaded.execution_context.artifacts[0]["artifact_id"] == "artifact_0"


def test_store_terminal_result_coheres_run_status(tmp_path):
    store = TaskRunStore(root=tmp_path / "runs")
    run = runtime_run().model_copy(update={"status": "running", "started_at": "2026-01-01T00:00:00+00:00"})
    store.create_run(run)

    store.save_result(run.run_id, TaskRunResult(run_id=run.run_id, status="blocked", summary="blocked"))
    loaded = store.get_run(run.run_id)

    assert loaded is not None
    assert loaded.status == "blocked"
    assert loaded.finished_at is not None
    assert loaded.current_step_id is None


def test_store_terminalizes_running_run_when_runtime_budget_exceeded(tmp_path):
    store = TaskRunStore(root=tmp_path / "runs")
    run = runtime_run().model_copy(
        update={
            "status": "running",
            "started_at": (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat(),
        }
    )
    store.create_run(run)

    result = store.terminalize_if_runtime_budget_exceeded(
        run.run_id,
        max_runtime_seconds=10,
        reason_code="TASKRUN_LIFECYCLE_TIMEOUT",
    )
    stored = store.get_run(run.run_id)
    events = store.get_events(run.run_id)

    assert result is not None
    assert result.status == "blocked"
    assert stored is not None
    assert stored.status == "blocked"
    assert stored.finished_at is not None
    assert "TASKRUN_LIFECYCLE_TIMEOUT" in stored.blocked_reasons
    assert events[-1].type == "run_blocked"


def test_store_runtime_budget_terminalization_is_idempotent(tmp_path):
    store = TaskRunStore(root=tmp_path / "runs")
    run = runtime_run().model_copy(
        update={
            "status": "running",
            "started_at": (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat(),
        }
    )
    store.create_run(run)

    first = store.terminalize_if_runtime_budget_exceeded(
        run.run_id,
        max_runtime_seconds=10,
        reason_code="TASKRUN_LIFECYCLE_TIMEOUT",
    )
    second = store.terminalize_if_runtime_budget_exceeded(
        run.run_id,
        max_runtime_seconds=10,
        reason_code="TASKRUN_LIFECYCLE_TIMEOUT",
    )
    events = store.get_events(run.run_id)

    assert first is not None
    assert second is not None
    assert [event.type for event in events].count("run_blocked") == 1
    assert [event.type for event in events].count("terminalization_already_applied") == 1
    assert events[-1].metadata["ignored"] is True


def test_runtime_storage_compaction_preserves_json_result_events_and_payload_refs(tmp_path):
    store = TaskRunStore(root=tmp_path / "runs")
    run = runtime_run()
    run_dir = store.root / run.run_id
    run_dir.mkdir(parents=True)
    raw = run.model_dump()
    raw["bootstrap_context"] = {
        "artifacts": [{"artifact_id": f"artifact_{index}", "evidence": "x" * 4000} for index in range(180)]
    }
    (run_dir / "run.json").write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "events.json").write_text(
        json.dumps(
            [
                TaskRunEvent(
                    event_id="event_1",
                    run_id=run.run_id,
                    sequence=1,
                    type="run_created",
                    status="created",
                    message="created",
                ).model_dump()
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (run_dir / "result.json").write_text(
        TaskRunResult(run_id=run.run_id, status="blocked", summary="blocked").model_dump_json(indent=2),
        encoding="utf-8",
    )
    before = (run_dir / "run.json").stat().st_size

    report = RuntimeStorageCompactionService(
        store=store,
        reports_root=tmp_path / "reports",
        large_run_threshold_bytes=1000,
    ).compact_task_runs(threshold_bytes=1000)
    loaded = store.get_run(run.run_id)

    assert report["files_compacted"] == 1
    assert (run_dir / "run.json").stat().st_size < before
    assert loaded is not None
    assert store.get_result(run.run_id) is not None
    assert store.get_events(run.run_id)
    assert (run_dir / "run_index.json").exists()
    assert list((run_dir / "payload_refs").glob("*.json"))
    assert report["deletes_evidence"] is False


def test_queue_reconcile_does_not_parse_terminal_historical_run_without_index(tmp_path):
    store = TaskRunStore(root=tmp_path / "runs")
    historical = store.root / "task_run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    historical.mkdir(parents=True)
    (historical / "run.json").write_text('{"status":"blocked","huge":"' + ("x" * 2_000_000) + '"}', encoding="utf-8")
    (historical / "result.json").write_text('{"run_id":"task_run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","status":"blocked","summary":"blocked"}', encoding="utf-8")

    snapshot = TaskQueueService(store=store).reconcile().snapshot

    assert snapshot.active_count == 0
    assert snapshot.pending_count == 0
    assert not (historical / "run_index.json").exists()


def test_create_run_is_not_blocked_by_terminal_historical_run_json(tmp_path):
    store = TaskRunStore(root=tmp_path / "runs")
    historical = store.root / "task_run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    historical.mkdir(parents=True)
    (historical / "run.json").write_text('{"status":"blocked","huge":"' + ("x" * 2_000_000) + '"}', encoding="utf-8")
    (historical / "result.json").write_text('{"run_id":"task_run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","status":"blocked","summary":"blocked"}', encoding="utf-8")
    runtime = TaskRuntimeService(store=store)

    started = time.perf_counter()
    execution = runtime.create_run(runtime_request())
    elapsed = time.perf_counter() - started

    assert execution.status in {"created", "queued", "running", "completed", "blocked"}
    assert elapsed < 2.0
