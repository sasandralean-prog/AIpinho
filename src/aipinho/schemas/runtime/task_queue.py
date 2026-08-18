from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class TaskQueueItem(AIpinhoModel):
    run_id: str
    session_id: str | None = None
    status: str
    priority: int
    created_at: str
    age_seconds: int
    approval_id: str | None = None
    approval_status: str | None = None
    auto_run_requested: bool = False
    requires_decision: bool = False
    expired_by_policy: bool = False


class TaskQueueSnapshot(AIpinhoModel):
    status: str = "ok"
    enabled: bool = True
    max_pending_tasks: int
    max_wait_seconds: int
    active_count: int = 0
    pending_count: int = 0
    requires_decision_count: int = 0
    total_visible: int = 0
    items: list[TaskQueueItem] = Field(default_factory=list)
    last_reconciled_at: str
    warnings: list[str] = Field(default_factory=list)


class TaskQueueReconciliationResult(AIpinhoModel):
    status: str = "ok"
    cancelled_run_ids: list[str] = Field(default_factory=list)
    cancelled_approval_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    snapshot: TaskQueueSnapshot
