from __future__ import annotations
from aipinho.schemas.runtime.task_cancellation import TaskCancellationRequest, TaskCancellationResult
from aipinho.services.runtime.task_run_event_service import TaskRunEventService
from aipinho.services.runtime.task_run_lifecycle_service import TaskRunLifecycleService
from aipinho.services.runtime.task_run_store import TaskRunStore

class TaskRunCancellationService:
    def __init__(self, store: TaskRunStore | None = None, lifecycle: TaskRunLifecycleService | None = None, events: TaskRunEventService | None = None) -> None:
        self.store = store or TaskRunStore()
        self.lifecycle = lifecycle or TaskRunLifecycleService()
        self.events = events or TaskRunEventService(self.store)

    def cancel(self, run_id: str, request: TaskCancellationRequest | None = None) -> TaskCancellationResult:
        run = self.store.get_run(run_id)
        if run is None: raise ValueError("task_run_not_found")
        if not self.lifecycle.can_cancel(run.status):
            return TaskCancellationResult(run_id=run_id, status=run.status, cancellation_requested=False, message="terminal_task_run_cannot_be_cancelled")
        data = request or TaskCancellationRequest()
        run.cancellation_requested = True
        run.cancellation_reason = data.reason
        run.revision += 1
        self.events.create(run_id, "run_cancel_requested", run.status, "TaskRun cancellation requested.", metadata={"reason": data.reason, "actor": data.requested_by.model_dump()})
        if run.status in {"created", "queued", "waiting_input"}:
            self.lifecycle.transition(run, "cancelled")
            self.events.create(run_id, "run_cancelled", "cancelled", "TaskRun cancelled before the next step.")
        self.store.update_run(run)
        return TaskCancellationResult(run_id=run_id, status=run.status, cancellation_requested=True, message="cancellation_recorded")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "task_run_cancellation", "best_effort_during_step": True}
