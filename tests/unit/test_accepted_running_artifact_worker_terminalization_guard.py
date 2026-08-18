from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.runtime.task_queue_service import TaskQueueService
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    AcceptedRunningWorkerTerminalityPolicy,
    PublicRuntimeResponsePolicy,
    ReadonlyAnalysisArtifactRuntimeService,
    ReadonlyArtifactExecution,
)
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService


def _run(
    runtime: TaskRuntimeService,
    *,
    status: str = "created",
    workspace: str = r"C:\Workspace\Generic",
    raw_prompt: str = "Produce governed artifacts.",
) -> TaskRun:
    run_id = f"task_run_{uuid4().hex}"
    run = TaskRun(
        run_id=run_id,
        task_id=f"task_{uuid4().hex}",
        operation_id=f"operation_{uuid4().hex}",
        task_run_id=run_id,
        source_type="direct",
        workspace=workspace,
        contract_type="analysis_readonly",
        operation_type="workspace_analysis_readonly",
        runtime_profile="readonly_analysis_artifact_runtime",
        requested_actions=["read_workspace"],
        intent_map={"raw_prompt": raw_prompt, "intent_type": "workspace_analysis_readonly"},
        status=status,  # type: ignore[arg-type]
        plan=TaskRunPlan(plan_id=f"plan_{uuid4().hex}", contract_type="analysis_readonly"),
    )
    runtime.store.create_run(run)
    return run


def _service(runtime: TaskRuntimeService, *, stall_ms: int = 30) -> ReadonlyAnalysisArtifactRuntimeService:
    return ReadonlyAnalysisArtifactRuntimeService(
        runtime=runtime,
        accepted_worker_terminality_policy=AcceptedRunningWorkerTerminalityPolicy(
            max_artifact_silence_ms=stall_ms,
            poll_interval_ms=5,
            max_worker_exit_grace_ms=1,
        ),
        public_response_policy=PublicRuntimeResponsePolicy(initial_response_budget_ms=25),
    )


def test_artifact_creation_started_without_terminal_artifact_persists_blocked_result(task_runtime_service: TaskRuntimeService) -> None:
    service = _service(task_runtime_service)
    run = _run(task_runtime_service)
    started = task_runtime_service.events.create(
        run.run_id,
        "artifact_creation_started",
        "running",
        "Artifact creation started.",
        metadata={"logical_path": "reports/example.md", "producer_step": "readonly_analysis_artifact_runtime"},
    )

    result = service._terminalize_accepted_worker_gap(  # noqa: SLF001 - guard contract unit
        run.run_id,
        reason_code="ARTIFACT_WORKER_STALLED_AFTER_ARTIFACT_CREATION_STARTED",
        message="Artifact worker stalled after artifact creation started.",
        artifact_event=started,
    )

    assert result is not None
    assert result.status == "blocked"
    assert result.source == "artifact_worker_terminalization_guard"
    assert result.validation["reason_code"] == "ARTIFACT_WORKER_STALLED_AFTER_ARTIFACT_CREATION_STARTED"
    assert result.completion is not None
    assert result.completion.status == "blocked"
    assert result.completion.safe_to_report_success is False
    persisted = task_runtime_service.store.get_result(run.run_id)
    updated = task_runtime_service.store.get_run(run.run_id)
    events = task_runtime_service.store.get_events(run.run_id)
    terminal_events = [event for event in events if event.type in {"run_completed", "run_partial", "run_failed", "run_cancelled", "run_blocked"}]
    assert persisted is not None
    assert updated is not None
    assert updated.status == "blocked"
    assert updated.finished_at
    assert len(terminal_events) == 1
    assert any(event.type == "artifact_failed" for event in events)


def test_artifact_terminal_event_prevents_guard_interference(task_runtime_service: TaskRuntimeService) -> None:
    service = _service(task_runtime_service)
    run = _run(task_runtime_service)
    started = task_runtime_service.events.create(
        run.run_id,
        "artifact_creation_started",
        "running",
        "Artifact creation started.",
        metadata={"logical_path": "reports/example.md", "producer_step": "readonly_analysis_artifact_runtime"},
    )
    task_runtime_service.events.create(
        run.run_id,
        "artifact_created",
        "completed",
        "Artifact created.",
        metadata={"logical_path": "reports/example.md", "created_event_source_id": started.event_id},
    )

    result = service._terminalize_accepted_worker_gap(  # noqa: SLF001 - guard contract unit
        run.run_id,
        reason_code="ARTIFACT_WORKER_STALLED_AFTER_ARTIFACT_CREATION_STARTED",
        message="Should not terminalize.",
    )

    assert result is None
    assert task_runtime_service.store.get_result(run.run_id) is None
    assert not any(event.type == "run_blocked" for event in task_runtime_service.store.get_events(run.run_id))


def test_terminalization_guard_is_idempotent(task_runtime_service: TaskRuntimeService) -> None:
    service = _service(task_runtime_service)
    run = _run(task_runtime_service)
    started = task_runtime_service.events.create(
        run.run_id,
        "artifact_creation_started",
        "running",
        "Artifact creation started.",
        metadata={"logical_path": "reports/example.md", "producer_step": "readonly_analysis_artifact_runtime"},
    )

    first = service._terminalize_accepted_worker_gap(  # noqa: SLF001 - guard contract unit
        run.run_id,
        reason_code="ARTIFACT_WORKER_STALLED_AFTER_ARTIFACT_CREATION_STARTED",
        message="Artifact worker stalled after artifact creation started.",
        artifact_event=started,
    )
    second = service._terminalize_accepted_worker_gap(  # noqa: SLF001 - guard contract unit
        run.run_id,
        reason_code="ARTIFACT_WORKER_STALLED_AFTER_ARTIFACT_CREATION_STARTED",
        message="Artifact worker stalled after artifact creation started.",
        artifact_event=started,
    )

    events = task_runtime_service.store.get_events(run.run_id)
    terminal_events = [event for event in events if event.type in {"run_completed", "run_partial", "run_failed", "run_cancelled", "run_blocked"}]
    assert first is not None
    assert second is not None
    assert second.status == first.status
    assert len(terminal_events) == 1


def test_existing_semantic_result_is_not_overwritten_by_guard(task_runtime_service: TaskRuntimeService) -> None:
    service = _service(task_runtime_service)
    run = _run(task_runtime_service, status="blocked")
    task_runtime_service.store.save_result(
        run.run_id,
        TaskRunResult(
            run_id=run.run_id,
            status="blocked",
            source="phase_semantic_completion_policy",
            summary="Semantic policy blocked the run.",
            validation={"status": "blocked", "reason_code": "MUSIC_INVENTORY_PARTIAL_NOT_ACCEPTED_BY_PHASE_CONTRACT"},
        ),
    )

    result = service._terminalize_accepted_worker_gap(  # noqa: SLF001 - guard contract unit
        run.run_id,
        reason_code="ARTIFACT_WORKER_STALLED_AFTER_ARTIFACT_CREATION_STARTED",
        message="Should not overwrite semantic result.",
        only_if_artifact_started=False,
    )

    assert result is not None
    assert result.source == "phase_semantic_completion_policy"
    assert result.validation["reason_code"] == "MUSIC_INVENTORY_PARTIAL_NOT_ACCEPTED_BY_PHASE_CONTRACT"


class ExceptionAfterAcceptedRuntime(ReadonlyAnalysisArtifactRuntimeService):
    def execute(self, *, request, workspace: str, label: str = "WORKSPACE_ANALYSIS_ARTIFACTS_READY") -> ReadonlyArtifactExecution:
        run = _run(self.runtime, workspace=workspace, raw_prompt=request.message)
        run.session_id = request.session_id
        self.runtime.store.update_run(run)
        time.sleep(0.08)
        self.runtime.events.create(
            run.run_id,
            "artifact_creation_started",
            "running",
            "Artifact creation started.",
            metadata={"logical_path": "reports/example.md", "producer_step": "readonly_analysis_artifact_runtime"},
        )
        raise RuntimeError("synthetic worker failure")


def test_background_worker_exception_after_accepted_running_terminalizes_taskrun(task_runtime_service: TaskRuntimeService) -> None:
    service = ExceptionAfterAcceptedRuntime(
        runtime=task_runtime_service,
        public_response_policy=PublicRuntimeResponsePolicy(initial_response_budget_ms=20),
        accepted_worker_terminality_policy=AcceptedRunningWorkerTerminalityPolicy(
            poll_interval_ms=5,
            max_artifact_silence_ms=1000,
            max_worker_exit_grace_ms=1,
        ),
    )

    execution = service.start_public_boundary(
        request=ChatRequest(message="Produce reports/example.md", session_id="chat_worker_exception"),
        workspace=r"C:\Workspace\Generic",
    )
    assert execution.response.status == "accepted_running"
    assert execution.run_id
    deadline = time.monotonic() + 2
    result = None
    terminal_events = []
    while time.monotonic() < deadline:
        result = task_runtime_service.store.get_result(execution.run_id)
        events = task_runtime_service.store.get_events(execution.run_id)
        terminal_events = [event for event in events if event.type in {"run_completed", "run_partial", "run_failed", "run_cancelled", "run_blocked"}]
        if result is not None and terminal_events:
            break
        time.sleep(0.02)

    assert result is not None
    assert result.status == "blocked"
    assert result.source == "artifact_worker_terminalization_guard"
    assert result.validation["reason_code"] in {
        "ARTIFACT_CREATION_EXCEPTION_AFTER_ACCEPTED_RUNNING",
        "ARTIFACT_WORKER_STALLED_AFTER_ARTIFACT_CREATION_STARTED",
    }
    assert len(terminal_events) == 1


class SilentExitRuntime(ReadonlyAnalysisArtifactRuntimeService):
    def execute(self, *, request, workspace: str, label: str = "WORKSPACE_ANALYSIS_ARTIFACTS_READY") -> ReadonlyArtifactExecution:
        run = _run(self.runtime, workspace=workspace, raw_prompt=request.message)
        run.session_id = request.session_id
        self.runtime.store.update_run(run)
        time.sleep(0.08)
        self.runtime.events.create(
            run.run_id,
            "artifact_creation_started",
            "running",
            "Artifact creation started.",
            metadata={"logical_path": "reports/example.md", "producer_step": "readonly_analysis_artifact_runtime"},
        )
        return ReadonlyArtifactExecution(
            response=ChatResponse(
                response_id=f"chat_{uuid4().hex}",
                session_id=request.session_id,
                status="blocked",
                message="worker exited without result",
                operation_type="workspace_analysis_readonly",
                intent={"intent_type": "workspace_analysis_readonly"},
                policy={"safe_to_report_success": False},
                is_final_answer=False,
                grounded=False,
            ),
            run_id=run.run_id,
            created_artifacts=[],
            validation={"status": "blocked", "safe_to_report_success": False},
        )


def test_background_worker_silent_exit_after_artifact_start_terminalizes_taskrun(task_runtime_service: TaskRuntimeService) -> None:
    service = SilentExitRuntime(
        runtime=task_runtime_service,
        public_response_policy=PublicRuntimeResponsePolicy(initial_response_budget_ms=20),
        accepted_worker_terminality_policy=AcceptedRunningWorkerTerminalityPolicy(
            poll_interval_ms=5,
            max_artifact_silence_ms=1000,
            max_worker_exit_grace_ms=1,
        ),
    )

    execution = service.start_public_boundary(
        request=ChatRequest(message="Produce reports/example.md", session_id="chat_worker_silent_exit"),
        workspace=r"C:\Workspace\Generic",
    )
    assert execution.response.status == "accepted_running"
    assert execution.run_id
    deadline = time.monotonic() + 2
    result = None
    while time.monotonic() < deadline:
        result = task_runtime_service.store.get_result(execution.run_id)
        if result is not None:
            break
        time.sleep(0.02)

    assert result is not None
    assert result.status == "blocked"
    assert result.source == "artifact_worker_terminalization_guard"
    assert result.validation["reason_code"] == "ARTIFACT_WORKER_EXITED_WITHOUT_TERMINAL_RESULT" or result.validation["reason_code"] == "ARTIFACT_WORKER_STALLED_AFTER_ARTIFACT_CREATION_STARTED"


def test_task_queue_reconcile_terminalizes_stalled_artifact_creation_when_guard_is_absent(
    task_runtime_service: TaskRuntimeService,
    monkeypatch,
) -> None:
    monkeypatch.setenv("AIPINHO_ARTIFACT_RENDER_MAX_ARTIFACT_SECONDS", "1")
    run = _run(task_runtime_service, status="running")
    old_timestamp = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    task_runtime_service.store.append_event(
        run.run_id,
        TaskRunEvent(
            event_id=f"task_run_event_{uuid4().hex}",
            run_id=run.run_id,
            sequence=len(task_runtime_service.store.get_events(run.run_id)) + 1,
            type="artifact_creation_started",
            status="running",
            message="Artifact creation started.",
            timestamp=old_timestamp,
            metadata={"logical_path": "reports/example.md", "producer_step": "readonly_analysis_artifact_runtime"},
        ),
    )

    queue = TaskQueueService(store=task_runtime_service.store)
    reconciliation = queue.reconcile()
    result = task_runtime_service.store.get_result(run.run_id)
    updated = task_runtime_service.store.get_run(run.run_id)
    events = task_runtime_service.store.get_events(run.run_id)
    terminal_events = [event for event in events if event.type in {"run_completed", "run_partial", "run_failed", "run_cancelled", "run_blocked"}]

    assert reconciliation.status == "degraded"
    assert result is not None
    assert result.status == "blocked"
    assert result.source == "artifact_worker_terminalization_guard"
    assert result.validation["reason_code"] == "ARTIFACT_CREATION_TIMEOUT_WITHOUT_TERMINAL_ARTIFACT"
    assert updated is not None
    assert updated.status == "blocked"
    assert updated.finished_at
    assert len(terminal_events) == 1
    assert any(event.type == "artifact_failed" for event in events)


def test_runtime_budget_terminalization_preserves_artifact_specific_reason(
    task_runtime_service: TaskRuntimeService,
) -> None:
    run = _run(task_runtime_service, status="running")
    run.started_at = (datetime.now(timezone.utc) - timedelta(seconds=5)).isoformat()
    task_runtime_service.store.update_run(run)
    task_runtime_service.store.append_event(
        run.run_id,
        TaskRunEvent(
            event_id=f"task_run_event_{uuid4().hex}",
            run_id=run.run_id,
            sequence=len(task_runtime_service.store.get_events(run.run_id)) + 1,
            type="artifact_creation_started",
            status="running",
            message="Artifact creation started.",
            metadata={"logical_path": "reports/example.md", "producer_step": "readonly_analysis_artifact_runtime"},
        ),
    )

    result = task_runtime_service.store.terminalize_if_runtime_budget_exceeded(
        run.run_id,
        max_runtime_seconds=0,
        reason_code="TASKRUN_LIFECYCLE_TIMEOUT",
    )
    events = task_runtime_service.store.get_events(run.run_id)
    terminal_events = [event for event in events if event.type in {"run_completed", "run_partial", "run_failed", "run_cancelled", "run_blocked"}]

    assert result is not None
    assert result.status == "blocked"
    assert result.source == "artifact_worker_terminalization_guard"
    assert result.validation["reason_code"] == "ARTIFACT_CREATION_TIMEOUT_WITHOUT_TERMINAL_ARTIFACT"
    assert result.finished_at
    assert len(terminal_events) == 1
    assert (terminal_events[0].metadata or {}).get("reason_code") == "ARTIFACT_CREATION_TIMEOUT_WITHOUT_TERMINAL_ARTIFACT"
