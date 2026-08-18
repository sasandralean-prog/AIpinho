from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


def _run(run_id: str | None = None, *, status: str = "running") -> TaskRun:
    run_id = run_id or f"task_run_{uuid4().hex}"
    return TaskRun(
        run_id=run_id,
        task_id="task_public_finalization",
        operation_id="operation_public_finalization",
        task_run_id=run_id,
        source_type="direct",
        session_id="chat_public_finalization",
        workspace=r"C:\Workspace\Generic",
        contract_type="analysis_readonly",
        operation_type="workspace_analysis_readonly",
        runtime_profile="readonly_analysis_artifact_runtime",
        requested_actions=["read_workspace"],
        intent_map={"raw_prompt": "Run readonly analysis"},
        status=status,  # type: ignore[arg-type]
        started_at=(datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat(),
        plan=TaskRunPlan(plan_id="plan_public_finalization", contract_type="analysis_readonly"),
    )


def test_timeout_blocked_finalizes_run_result_and_single_terminal_event(task_runtime_store) -> None:
    run = _run()
    task_runtime_store.create_run(run)

    first = task_runtime_store.terminalize_if_runtime_budget_exceeded(
        run.run_id,
        max_runtime_seconds=0,
        reason_code="PUBLIC_CHAT_RESPONSE_BUDGET_EXCEEDED",
    )
    second = task_runtime_store.terminalize_if_runtime_budget_exceeded(
        run.run_id,
        max_runtime_seconds=0,
        reason_code="PUBLIC_CHAT_RESPONSE_BUDGET_EXCEEDED",
    )

    reloaded = task_runtime_store.get_run(run.run_id)
    events = task_runtime_store.get_events(run.run_id)
    terminal_events = [event for event in events if event.type == "run_blocked"]
    ignored_events = [event for event in events if event.type == "terminalization_already_applied"]
    assert first is not None
    assert second is not None
    assert reloaded is not None
    assert reloaded.status == "blocked"
    assert reloaded.finished_at
    assert first.status == "blocked"
    assert first.validation["status"] == "blocked"
    assert len(terminal_events) == 1
    assert len(ignored_events) == 1


def test_summary_reports_timeout_blocked_public_boundary(task_runtime_store) -> None:
    run = _run()
    task_runtime_store.create_run(run)
    task_runtime_store.terminalize_if_runtime_budget_exceeded(
        run.run_id,
        max_runtime_seconds=0,
        reason_code="PUBLIC_CHAT_RESPONSE_BUDGET_EXCEEDED",
    )

    summary = UniversalTaskSessionService(store=task_runtime_store).summary(run.run_id)

    assert summary is not None
    assert summary["public_response_boundary"]["status"] == "timeout_blocked"
    assert summary["public_response_boundary"]["result_finalized"] is True
    assert summary["public_response_boundary"]["terminal_event_count"] == 1
    assert summary["public_response_boundary"]["safe_to_report_success"] is False


def test_late_artifact_event_does_not_change_terminal_success(task_runtime_store) -> None:
    run = _run()
    task_runtime_store.create_run(run)
    task_runtime_store.terminalize_if_runtime_budget_exceeded(
        run.run_id,
        max_runtime_seconds=0,
        reason_code="PUBLIC_CHAT_RESPONSE_BUDGET_EXCEEDED",
    )
    task_runtime_store.append_event(
        run.run_id,
        TaskRunEvent(
            event_id="task_run_event_late_artifact_rejected",
            run_id=run.run_id,
            sequence=len(task_runtime_store.get_events(run.run_id)) + 1,
            type="artifact_late_rejected",
            status="rejected",
            message="Late artifact rejected after terminal state.",
            metadata={"reason_code": "ARTIFACT_RENDER_LATE_ARTIFACT_REJECTED", "safe_to_use": False},
        ),
    )

    summary = UniversalTaskSessionService(store=task_runtime_store).summary(run.run_id)

    assert summary is not None
    assert summary["public_response_boundary"]["terminal_event_count"] == 1
    assert summary["public_response_boundary"]["safe_to_report_success"] is False
    assert any(event.type == "artifact_late_rejected" for event in task_runtime_store.get_events(run.run_id))


def test_active_runtime_truth_uses_light_projection_without_timeline(task_runtime_store, monkeypatch) -> None:
    run = _run(status="running")
    task_runtime_store.create_run(run)
    service = TaskRuntimeService(store=task_runtime_store)

    def fail_timeline_build(run_id: str):
        raise AssertionError("timeline_build_not_required_for_active_light_truth")

    monkeypatch.setattr(service.timeline, "build", fail_timeline_build)

    truth = service.get_runtime_truth(run.run_id)

    assert truth is not None
    assert truth.status == "running"
    assert truth.safe_to_report_success is False
