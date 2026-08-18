from __future__ import annotations

import os
from datetime import datetime, timezone
from threading import RLock
from typing import Callable

from aipinho.core.paths import PATHS
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.runtime.task_cancellation import TaskCancellationRequest
from aipinho.schemas.runtime.task_queue import (
    TaskQueueItem,
    TaskQueueReconciliationResult,
    TaskQueueSnapshot,
)
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.runtime.task_run_cancellation_service import TaskRunCancellationService
from aipinho.services.runtime.task_run_lifecycle_service import TaskRunLifecycleService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.task_block_cause_service import TaskBlockCauseService
from aipinho.services.runtime.task_run_trace_service import TaskRunTraceService
from aipinho.utils.yaml_loader import load_yaml_file


class TaskQueueService:
    _reconcile_lock = RLock()

    def __init__(
        self,
        store: TaskRunStore | None = None,
        lifecycle: TaskRunLifecycleService | None = None,
        cancellation: TaskRunCancellationService | None = None,
        approvals: ApprovalService | None = None,
        now_provider: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store or TaskRunStore()
        self.lifecycle = lifecycle or TaskRunLifecycleService()
        self.cancellation = cancellation or TaskRunCancellationService(
            self.store,
            self.lifecycle,
        )
        self.approvals = approvals or ApprovalService()
        self.block_causes = TaskBlockCauseService()
        self.trace = TaskRunTraceService()
        self.now_provider = now_provider or (lambda: datetime.now(timezone.utc))
        self.policy = load_yaml_file(
            PATHS.config_root / "runtime" / "task_queue_policy.yaml",
            critical=True,
            root=PATHS.config_root / "runtime",
        )

    def reconcile(self) -> TaskQueueReconciliationResult:
        with self._reconcile_lock:
            cancelled_runs: list[str] = []
            cancelled_approvals: list[str] = []
            warnings: list[str] = []
            if not self.enabled:
                snapshot = self._build_snapshot(warnings=["task_queue_disabled"])
                return TaskQueueReconciliationResult(
                    status="disabled",
                    snapshot=snapshot,
                    warnings=list(snapshot.warnings),
                )

            queue_statuses = self.pending_states | self.active_states
            runs = self.store.list_queue_runs(active_statuses=queue_statuses, limit=1000)
            self._reconcile_approval_states(
                runs,
                cancelled_runs,
                cancelled_approvals,
                warnings,
            )
            self._reconcile_artifact_creation_terminality_gaps(runs, warnings)
            runs = self.store.list_queue_runs(active_statuses=queue_statuses, limit=1000)
            if self.auto_cancel_expired:
                expired = [
                    run
                    for run in runs
                    if run.status in self.pending_states
                    and self._age_seconds(run.created_at, warnings) > self.max_wait_seconds
                ]
                for run in sorted(expired, key=lambda item: item.created_at):
                    self._cancel_run(
                        run.run_id,
                        run.approval_id,
                        "queue_wait_timeout_exceeded",
                        cancelled_runs,
                        cancelled_approvals,
                        warnings,
                    )

            runs = self.store.list_queue_runs(active_statuses=queue_statuses, limit=1000)
            pending = [run for run in runs if run.status in self.pending_states]
            overflow = max(0, len(pending) - self.max_pending_tasks)
            if overflow and self.overflow_strategy == "cancel_oldest_pending":
                for run in sorted(pending, key=lambda item: item.created_at)[:overflow]:
                    self._cancel_run(
                        run.run_id,
                        run.approval_id,
                        "queue_capacity_exceeded",
                        cancelled_runs,
                        cancelled_approvals,
                        warnings,
                    )

            snapshot = self._build_snapshot(warnings=warnings)
            return TaskQueueReconciliationResult(
                status="degraded" if warnings else "ok",
                cancelled_run_ids=cancelled_runs,
                cancelled_approval_ids=cancelled_approvals,
                warnings=warnings,
                snapshot=snapshot,
            )

    def _reconcile_artifact_creation_terminality_gaps(self, runs, warnings: list[str]) -> None:
        max_silence_seconds = self.artifact_creation_terminality_seconds
        for run in runs:
            if run.status not in self.active_states:
                continue
            result = self.store.terminalize_if_artifact_creation_stalled(
                run.run_id,
                max_silence_seconds=max_silence_seconds,
                reason_code="ARTIFACT_CREATION_TIMEOUT_WITHOUT_TERMINAL_ARTIFACT",
                result_source="artifact_worker_terminalization_guard",
            )
            if result is not None:
                reason = (
                    result.validation.get("reason_code")
                    if isinstance(result.validation, dict)
                    else "ARTIFACT_CREATION_TIMEOUT_WITHOUT_TERMINAL_ARTIFACT"
                )
                warnings.append(f"artifact_creation_terminality_gap_reconciled:{run.run_id}:{reason}")

    def snapshot(self) -> TaskQueueSnapshot:
        return self._build_snapshot()

    def _build_snapshot(self, warnings: list[str] | None = None) -> TaskQueueSnapshot:
        now = self._now()
        local_warnings = list(warnings or [])
        items: list[TaskQueueItem] = []
        for run in self.store.list_queue_runs(active_statuses=self.pending_states | self.active_states, limit=1000):
            if self.lifecycle.is_terminal(run.status):
                continue
            age_seconds = self._age_seconds(run.created_at, local_warnings, now=now)
            approval_status = None
            if run.approval_id:
                approval = self.approvals.get_approval(run.approval_id)
                approval_status = approval.status if approval is not None else "missing"
            items.append(
                TaskQueueItem(
                    run_id=run.run_id,
                    session_id=run.session_id,
                    status=run.status,
                    priority=self.state_priority.get(run.status, 100),
                    created_at=run.created_at,
                    age_seconds=age_seconds,
                    approval_id=run.approval_id,
                    approval_status=approval_status,
                    auto_run_requested=run.auto_run_requested,
                    requires_decision=(
                        approval_status == "pending"
                        or (run.status == "waiting_input" and approval_status is None)
                    ),
                    expired_by_policy=(
                        run.status in self.pending_states
                        and age_seconds > self.max_wait_seconds
                    ),
                )
            )
        items.sort(
            key=lambda item: (
                item.priority,
                -self._timestamp(item.created_at, local_warnings),
            )
        )
        active_count = sum(item.status in self.active_states for item in items)
        pending_count = sum(item.status in self.pending_states for item in items)
        requires_decision_count = sum(item.requires_decision for item in items)
        return TaskQueueSnapshot(
            status="degraded" if local_warnings else "ok",
            enabled=self.enabled,
            max_pending_tasks=self.max_pending_tasks,
            max_wait_seconds=self.max_wait_seconds,
            active_count=active_count,
            pending_count=pending_count,
            requires_decision_count=requires_decision_count,
            total_visible=len(items),
            items=items,
            last_reconciled_at=now.isoformat(),
            warnings=list(dict.fromkeys(local_warnings)),
        )

    def _reconcile_approval_states(
        self,
        runs,
        cancelled_runs: list[str],
        cancelled_approvals: list[str],
        warnings: list[str],
    ) -> None:
        for run in runs:
            if self.lifecycle.is_terminal(run.status) or not run.approval_id:
                continue
            try:
                approval = self.approvals.get_approval(run.approval_id)
            except Exception as exc:
                warnings.append(
                    f"task_queue_approval_read_failed:{run.approval_id}:{type(exc).__name__}"
                )
                continue
            if approval is None:
                self._cancel_run(
                    run.run_id,
                    None,
                    "linked_approval_missing",
                    cancelled_runs,
                    cancelled_approvals,
                    warnings,
                )
                continue
            if approval.status == "pending":
                if run.status in {"created", "queued"}:
                    self.lifecycle.transition(run, "waiting_input")
                    self.store.update_run(run)
                    self.cancellation.events.create(
                        run.run_id,
                        "run_waiting_input",
                        "waiting_input",
                        "TaskRun is waiting for an explicit approval decision.",
                        metadata={"approval_id": run.approval_id},
                    )
                continue
            if approval.status == "approved":
                self._resume_approved_approval(run, approval, warnings)
                continue
            if approval.status == "rejected":
                self._cancel_denied_approval(run, warnings)
                continue
            if approval.status in {"cancelled", "expired", "invalidated_by_policy_change"}:
                self._cancel_run(
                    run.run_id,
                    None,
                    f"linked_approval_{approval.status}",
                    cancelled_runs,
                    cancelled_approvals,
                    warnings,
                )

    def _resume_approved_approval(self, run, approval, warnings: list[str]) -> None:
        try:
            if "approval_required" in run.blocked_reasons:
                run.blocked_reasons = [
                    reason for reason in run.blocked_reasons if reason != "approval_required"
                ]
            run.approval_snapshot = self.store.sanitize(approval.model_dump())
            run.auto_run_requested = True
            if run.status == "created" and self.lifecycle.can_transition(run.status, "queued"):
                self.lifecycle.transition(run, "queued")
            self.store.update_run(run)
            self.cancellation.events.create(
                run.run_id,
                "approval_approved",
                run.status,
                "Approval aprovado; TaskRun liberada para execucao governada.",
                metadata={"approval_id": run.approval_id},
            )
            self.cancellation.events.create(
                run.run_id,
                "task_resumed_after_approval",
                run.status,
                "TaskRun marcada para retomada pela fila governada.",
                metadata={"approval_id": run.approval_id, "auto_run_requested": True},
            )
        except Exception as exc:
            warnings.append(f"task_queue_approval_resume_failed:{run.run_id}:{type(exc).__name__}")

    def _cancel_denied_approval(self, run, warnings: list[str]) -> None:
        try:
            if "approval_required" in run.blocked_reasons:
                run.blocked_reasons = [
                    reason for reason in run.blocked_reasons if reason != "approval_required"
                ]
            if "approval_denied" not in run.blocked_reasons:
                run.blocked_reasons.append("approval_denied")
            self.lifecycle.transition(run, "blocked")
            cause = self.block_causes.build(run, ["approval_denied"], blocked_stage="approval_denied")
            run.block_cause = cause
            run.trace.append(
                self.trace.item(
                    "approval_denied",
                    "blocked",
                    "approval_denied",
                    source="services/runtime/task_queue_service.py",
                    data={"approval_id": run.approval_id, "block_cause": cause.model_dump()},
                )
            )
            denied = self.cancellation.events.create(
                run.run_id,
                "approval_denied",
                "blocked",
                "The required approval was denied; no side effect will be executed.",
                metadata={"approval_id": run.approval_id, "block_cause": cause.model_dump()},
            )
            self.cancellation.events.create(
                run.run_id,
                "task_blocked",
                "blocked",
                "Task blocked because the required approval was denied.",
                metadata={"approval_denied_event_id": denied.event_id},
            )
            self.store.update_run(run)
            self.store.save_trace(run.run_id, run.trace)
        except Exception as exc:
            warnings.append(f"task_queue_approval_cancel_failed:{run.run_id}:{type(exc).__name__}")

    def _cancel_run(
        self,
        run_id: str,
        approval_id: str | None,
        reason: str,
        cancelled_runs: list[str],
        cancelled_approvals: list[str],
        warnings: list[str],
    ) -> None:
        try:
            result = self.cancellation.cancel(
                run_id,
                TaskCancellationRequest(
                    reason=reason,
                    requested_by=Actor(type="system", id="task_queue_service"),
                ),
            )
        except Exception as exc:
            warnings.append(f"task_queue_cancel_failed:{run_id}:{type(exc).__name__}")
            return
        if result.cancellation_requested:
            cancelled_runs.append(run_id)
        if not approval_id or not self.cancel_linked_pending_approval:
            return
        try:
            approval = self.approvals.get_approval(approval_id)
            if approval is not None and approval.status == "pending":
                self.approvals.cancel(
                    approval_id,
                    actor=Actor(type="system", id="task_queue_service"),
                    reason=reason,
                )
                cancelled_approvals.append(approval_id)
        except Exception as exc:
            warnings.append(
                f"task_queue_approval_cancel_failed:{approval_id}:{type(exc).__name__}"
            )

    def _age_seconds(
        self,
        created_at: str,
        warnings: list[str],
        *,
        now: datetime | None = None,
    ) -> int:
        created = self._parse_datetime(created_at, warnings)
        if created is None:
            return 0
        return max(0, int(((now or self._now()) - created).total_seconds()))

    def _timestamp(self, value: str, warnings: list[str]) -> float:
        parsed = self._parse_datetime(value, warnings)
        return parsed.timestamp() if parsed is not None else 0.0

    @staticmethod
    def _parse_datetime(value: str, warnings: list[str]) -> datetime | None:
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            warnings.append("task_queue_invalid_created_at")
            return None

    def _now(self) -> datetime:
        value = self.now_provider()
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)

    @property
    def settings(self) -> dict[str, object]:
        value = self.policy.get("queue", {})
        return value if isinstance(value, dict) else {}

    @property
    def auto_run_settings(self) -> dict[str, object]:
        value = self.policy.get("auto_run", {})
        return value if isinstance(value, dict) else {}

    @property
    def enabled(self) -> bool:
        return bool(self.settings.get("enabled", True))

    @property
    def max_pending_tasks(self) -> int:
        return max(1, int(self.settings.get("max_pending_tasks", 25) or 25))

    @property
    def max_wait_seconds(self) -> int:
        return max(60, int(self.settings.get("max_wait_seconds", 86400) or 86400))

    @property
    def reconcile_interval_seconds(self) -> int:
        return max(
            5,
            int(self.settings.get("reconcile_interval_seconds", 60) or 60),
        )

    @property
    def artifact_creation_terminality_seconds(self) -> float:
        configured = self.settings.get("artifact_creation_terminality_seconds")
        if configured is None:
            configured = os.environ.get(
                "AIPINHO_ACCEPTED_WORKER_ARTIFACT_STALL_MS",
                None,
            )
            if configured is not None:
                return max(1.0, float(configured) / 1000)
            configured = min(
                60.0,
                float(
                    os.environ.get(
                        "AIPINHO_ARTIFACT_RENDER_MAX_ARTIFACT_SECONDS",
                        os.environ.get("AIPINHO_PHASE1_MAX_ARTIFACT_RENDER_SECONDS", "420"),
                    )
                ),
            )
        return max(1.0, float(configured or 60))

    @property
    def auto_cancel_expired(self) -> bool:
        return bool(self.settings.get("auto_cancel_expired", True))

    @property
    def cancel_linked_pending_approval(self) -> bool:
        return bool(self.settings.get("cancel_linked_pending_approval", True))

    @property
    def overflow_strategy(self) -> str:
        return str(self.settings.get("overflow_strategy", "cancel_oldest_pending"))

    @property
    def active_states(self) -> set[str]:
        return set(self.settings.get("active_states", ["running"]) or [])

    @property
    def pending_states(self) -> set[str]:
        return set(
            self.settings.get(
                "pending_states",
                ["waiting_input", "queued", "created"],
            )
            or []
        )

    @property
    def state_priority(self) -> dict[str, int]:
        configured = self.settings.get("state_priority", {})
        if not isinstance(configured, dict):
            return {}
        return {str(key): int(value) for key, value in configured.items()}

    @property
    def auto_run_enabled(self) -> bool:
        return bool(self.auto_run_settings.get("enabled", False))

    @property
    def auto_run_requires_explicit_request(self) -> bool:
        return bool(self.auto_run_settings.get("require_explicit_request", True))
