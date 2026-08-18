from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from tests.support.runtime_fixtures import runtime_run
from aipinho.services.runtime.task_queue_service import TaskQueueService


NOW = datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc)


class FakeApprovalService:
    def __init__(self) -> None:
        self.statuses: dict[str, str] = {}
        self.cancelled: list[str] = []

    def get_approval(self, approval_id: str):
        status = self.statuses.get(approval_id)
        return SimpleNamespace(approval_id=approval_id, status=status) if status else None

    def cancel(self, approval_id: str, **_kwargs):
        self.statuses[approval_id] = "cancelled"
        self.cancelled.append(approval_id)
        return None, self.get_approval(approval_id)


def make_run(
    suffix: str,
    *,
    status: str = "created",
    age: timedelta = timedelta(),
    approval_id: str | None = None,
):
    return runtime_run(status=status).model_copy(
        update={
            "run_id": f"task_run_{suffix * 32}",
            "created_at": (NOW - age).isoformat(),
            "approval_id": approval_id,
        }
    )


def queue_service(task_runtime_store, approvals=None) -> TaskQueueService:
    service = TaskQueueService(
        store=task_runtime_store,
        approvals=approvals or FakeApprovalService(),
        now_provider=lambda: NOW,
    )
    service.policy["queue"]["max_pending_tasks"] = 25
    service.policy["queue"]["max_wait_seconds"] = 86400
    return service


def test_queue_prioritizes_active_then_recent_pending(task_runtime_store):
    task_runtime_store.create_run(make_run("a", status="queued", age=timedelta(hours=2)))
    task_runtime_store.create_run(make_run("b", status="running", age=timedelta(days=2)))
    task_runtime_store.create_run(make_run("c", status="queued", age=timedelta(hours=1)))

    snapshot = queue_service(task_runtime_store).snapshot()

    assert [item.status for item in snapshot.items] == ["running", "queued", "queued"]
    assert [item.run_id for item in snapshot.items[1:]] == [
        f"task_run_{'c' * 32}",
        f"task_run_{'a' * 32}",
    ]
    assert snapshot.pending_count == 2
    assert snapshot.requires_decision_count == 0


def test_queue_cancels_pending_task_after_configured_wait(task_runtime_store):
    expired = make_run("a", age=timedelta(days=1, seconds=1))
    task_runtime_store.create_run(expired)

    result = queue_service(task_runtime_store).reconcile()

    assert result.cancelled_run_ids == [expired.run_id]
    assert task_runtime_store.get_run(expired.run_id).status == "cancelled"


def test_queue_never_expires_running_task_by_queue_age(task_runtime_store):
    running = make_run("a", status="running", age=timedelta(days=3))
    task_runtime_store.create_run(running)

    result = queue_service(task_runtime_store).reconcile()

    assert result.cancelled_run_ids == []
    assert task_runtime_store.get_run(running.run_id).status == "running"


def test_queue_overflow_cancels_oldest_pending_and_keeps_recent(task_runtime_store):
    oldest = make_run("a", age=timedelta(hours=3))
    middle = make_run("b", age=timedelta(hours=2))
    newest = make_run("c", age=timedelta(hours=1))
    for run in (oldest, middle, newest):
        task_runtime_store.create_run(run)
    service = queue_service(task_runtime_store)
    service.policy["queue"]["max_pending_tasks"] = 2

    result = service.reconcile()

    assert result.cancelled_run_ids == [oldest.run_id]
    assert task_runtime_store.get_run(oldest.run_id).status == "cancelled"
    assert task_runtime_store.get_run(newest.run_id).status == "created"


def test_queue_cancels_linked_pending_approval(task_runtime_store):
    approvals = FakeApprovalService()
    approvals.statuses["approval_queue"] = "pending"
    run = make_run(
        "a",
        status="waiting_input",
        age=timedelta(days=2),
        approval_id="approval_queue",
    )
    task_runtime_store.create_run(run)

    result = queue_service(task_runtime_store, approvals=approvals).reconcile()

    assert result.cancelled_approval_ids == ["approval_queue"]
    assert approvals.cancelled == ["approval_queue"]


def test_queue_reconciliation_is_idempotent(task_runtime_store):
    expired = make_run("a", age=timedelta(days=2))
    task_runtime_store.create_run(expired)
    service = queue_service(task_runtime_store)

    first = service.reconcile()
    second = service.reconcile()

    assert first.cancelled_run_ids == [expired.run_id]
    assert second.cancelled_run_ids == []
