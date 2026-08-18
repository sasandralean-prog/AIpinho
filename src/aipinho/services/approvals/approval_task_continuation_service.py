from __future__ import annotations

from typing import Any

from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.runtime.task_cancellation import TaskCancellationRequest
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.runtime.task_run_cancellation_service import TaskRunCancellationService
from aipinho.services.runtime.task_run_event_service import TaskRunEventService
from aipinho.services.runtime.task_run_lifecycle_service import TaskRunLifecycleService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.utils.yaml_loader import load_yaml_file
from aipinho.core.paths import PATHS
from aipinho.services.orchestration.executable_plan_service import ExecutablePlanService


class ApprovalTaskContinuationService:
    """Resume or reconcile TaskRuns after an explicit approval decision.

    The approval endpoint records the human decision. This service only releases
    an already linked TaskRun back to the governed runtime queue; the runtime
    guard still rechecks policy before any side effect happens.
    """

    def __init__(
        self,
        *,
        approvals: ApprovalService | None = None,
        store: TaskRunStore | None = None,
        lifecycle: TaskRunLifecycleService | None = None,
        events: TaskRunEventService | None = None,
    ) -> None:
        self.approvals = approvals or ApprovalService()
        self.store = store or TaskRunStore()
        self.lifecycle = lifecycle or TaskRunLifecycleService()
        self.events = events or TaskRunEventService(self.store)
        self.executable_plans = ExecutablePlanService()
        self.policy = load_yaml_file(
            PATHS.config_root / "policies" / "approval_lifecycle_policy.yaml",
            critical=True,
            root=PATHS.config_root / "policies",
        )

    def after_decision(self, approval: ApprovalRequest, *, auto_process: bool = True) -> dict[str, Any]:
        if approval.status == "approved":
            return self._resume_approved(approval, auto_process=auto_process)
        if approval.status in {"rejected", "cancelled"}:
            return self._reconcile_negative(approval)
        return {
            "status": "noop",
            "reason_code": f"approval_status_{approval.status}",
            "approval_id": approval.approval_id,
            "resumed": False,
        }

    def approve_safe_batch_for_task(self, task_id: str, *, actor=None, reason: str = "") -> dict[str, Any]:
        approvals = self.approvals.safe_batch_for_task(task_id)
        if not approvals:
            return {
                "status": "blocked",
                "reason_code": "no_safe_pending_approvals",
                "task_id": task_id,
                "approvals": [],
                "resume_results": [],
            }
        decisions = self.approvals.approve_batch(
            [approval.approval_id for approval in approvals],
            actor=actor,
            reason=reason or "safe_batch_approved",
            safe_only=True,
        )
        resume_results = [
            self.after_decision(approval, auto_process=False)
            for _decision, approval in decisions
        ]
        process = self._process_queue_if_enabled()
        return {
            "status": "ok",
            "task_id": task_id,
            "approvals": [approval.model_dump() for _decision, approval in decisions],
            "decisions": [decision.model_dump() for decision, _approval in decisions],
            "resume_results": resume_results,
            "queue_process": process,
        }

    def _resume_approved(self, approval: ApprovalRequest, *, auto_process: bool) -> dict[str, Any]:
        if not self._resume_enabled():
            return {
                "status": "recorded",
                "reason_code": "approval_resume_disabled_by_config",
                "approval_id": approval.approval_id,
                "resumed": False,
            }
        run_ref = approval.run_id or approval.task_id
        if not run_ref:
            created = self._create_run_from_approved_preview(approval, auto_process=auto_process)
            if created is not None:
                return created
            return {
                "status": "recorded",
                "reason_code": "approval_not_linked_to_task_run",
                "approval_id": approval.approval_id,
                "resumed": False,
            }
        run = self._find_linked_run(approval)
        if run is None:
            return {
                "status": "recorded",
                "reason_code": "linked_task_run_not_found",
                "approval_id": approval.approval_id,
                "run_id": run_ref,
                "resumed": False,
            }
        if self.lifecycle.is_terminal(run.status):
            return {
                "status": "noop",
                "reason_code": "task_run_terminal",
                "approval_id": approval.approval_id,
                "run_id": run.run_id,
                "run_status": run.status,
                "resumed": False,
            }
        if run.approval_id != approval.approval_id:
            return {
                "status": "blocked",
                "reason_code": "approval_task_mismatch",
                "approval_id": approval.approval_id,
                "run_id": run.run_id,
                "resumed": False,
            }
        if "approval_required" in run.blocked_reasons:
            run.blocked_reasons = [reason for reason in run.blocked_reasons if reason != "approval_required"]
        run.approval_snapshot = self.store.sanitize(approval.model_dump())
        run.auto_run_requested = True
        if run.status == "created" and self.lifecycle.can_transition(run.status, "queued"):
            self.lifecycle.transition(run, "queued")
        self.store.update_run(run)
        self.events.create(
            run.run_id,
            "approval_approved",
            "approved",
            "Approval aprovado; runtime governado pode retomar a task.",
            metadata={"approval_id": approval.approval_id, "scope": approval.approval_scope},
        )
        self.events.create(
            run.run_id,
            "task_resumed_after_approval",
            "queued" if run.status == "queued" else run.status,
            "Task liberada para retomada pela fila governada apos approval.",
            metadata={"approval_id": approval.approval_id, "auto_run_requested": True},
        )
        process = self._process_queue_if_enabled() if auto_process else {"status": "not_requested"}
        return {
            "status": "ok",
            "approval_id": approval.approval_id,
            "run_id": run.run_id,
            "run_status": (self.store.get_run(run.run_id) or run).status,
            "resumed": True,
            "queue_process": process,
        }

    def _create_run_from_approved_preview(self, approval: ApprovalRequest, *, auto_process: bool) -> dict[str, Any] | None:
        if not approval.preview_id:
            return None
        try:
            from aipinho.services.orchestration.task_contract_draft_service import TaskContractDraftService
            from aipinho.services.runtime.task_runtime_service import TaskRuntimeService

            draft = self.approvals.draft_store.get(approval.draft_id)
            plan = self.executable_plans.validate_draft(draft)
            if not plan["valid"]:
                approval.resume_status = "approved_but_no_executable_plan"
                approval.block_reason_code = str(plan["reason_code"])
                approval.execution_status = "blocked"
                approval.updated_at = self._utc_now()
                self.approvals.store.save(approval)
                self.approvals.append_event(
                    approval.approval_id,
                    "approval_approved_but_no_executable_plan",
                    "Approval aprovado, mas a execucao nao foi iniciada porque o preview nao contem plano executavel.",
                    {
                        "preview_id": approval.preview_id,
                        "draft_id": approval.draft_id,
                        "reason_code": plan["reason_code"],
                        "files_written": False,
                    },
                )
                return {
                    "status": "blocked",
                    "reason_code": "approved_but_no_executable_plan",
                    "approval_id": approval.approval_id,
                    "preview_id": approval.preview_id,
                    "draft_id": approval.draft_id,
                    "resumed": False,
                    "files_written": False,
                    "missing_plan": plan["reason_code"],
                }
            runtime = TaskRuntimeService(
                store=self.store,
                drafts=TaskContractDraftService(store=self.approvals.draft_store),
                previews=self.approvals.preview_service,
                approvals=self.approvals,
            )
            run = runtime.create_from_preview(
                approval.preview_id,
                {
                    "approval_id": approval.approval_id,
                    "start_immediately": True,
                    "include_trace": True,
                },
            )
            process = runtime.process_queue() if auto_process else {"status": "not_requested"}
            latest = self.store.get_run(run.run_id) or run
            approval.run_id = latest.run_id
            approval.task_id = latest.task_id or approval.task_id
            failure_details = self._run_failure_details(latest.run_id)
            reason_code = next(iter(latest.blocked_reasons), None) or failure_details.get("reason_code")
            approval.resume_status = latest.status
            approval.block_reason_code = reason_code if latest.status in {"blocked", "failed", "cancelled"} else None
            approval.execution_status = self._execution_status_for_run(latest.status)
            approval.updated_at = self._utc_now()
            self.approvals.store.save(approval)
            result = {
                "status": self._resume_status_for_run(latest.status),
                "result_code": "task_run_created_from_approved_preview",
                "approval_id": approval.approval_id,
                "run_id": latest.run_id,
                "run_status": latest.status,
                "block_reason_code": reason_code if latest.status == "blocked" else None,
                "resumed": True,
                "queue_process": process,
            }
            if failure_details:
                result.update(failure_details)
            if latest.status in {"blocked", "failed", "cancelled"}:
                result["reason_code"] = (
                    reason_code
                    or result.get("reason_code")
                    or f"task_run_{latest.status}_after_approval"
                )
            return result
        except Exception as exc:
            return {
                "status": "recorded",
                "reason_code": "approved_preview_task_run_creation_failed",
                "approval_id": approval.approval_id,
                "resumed": False,
                "error_type": type(exc).__name__,
            }

    @staticmethod
    def _utc_now() -> str:
        from aipinho.services.session.session_store import utc_now

        return utc_now()

    @staticmethod
    def _resume_status_for_run(status: str) -> str:
        if status in {"completed", "partial", "queued", "running", "created", "waiting_input"}:
            return "ok"
        if status in {"blocked", "failed", "cancelled", "expired"}:
            return status
        return "ok"

    @staticmethod
    def _execution_status_for_run(status: str) -> str:
        if status in {"completed", "partial"}:
            return "executed"
        if status in {"blocked", "failed", "cancelled", "expired"}:
            return status
        return "queued"

    def _run_failure_details(self, run_id: str) -> dict[str, Any]:
        result = self.store.get_result(run_id)
        if result is None:
            return {}
        for step in result.step_summaries:
            if not isinstance(step, dict):
                continue
            step_status = str(step.get("status") or "").casefold()
            if step_status not in {"failed", "blocked", "cancelled"}:
                continue
            output = step.get("output_summary") if isinstance(step.get("output_summary"), dict) else {}
            violations = step.get("violations") if isinstance(step.get("violations"), list) else []
            reason_code = (
                output.get("reason_code")
                or next((str(item) for item in violations if item), None)
                or f"task_step_{step_status}"
            )
            return {
                "reason_code": reason_code,
                "failed_step_id": step.get("step_id"),
                "failed_step_type": step.get("step_type"),
                "failed_step_status": step_status,
                "violations": violations,
                "result_status": result.status,
            }
        if result.status in {"failed", "blocked", "cancelled"}:
            return {
                "reason_code": f"task_run_{result.status}",
                "result_status": result.status,
            }
        return {}

    def _reconcile_negative(self, approval: ApprovalRequest) -> dict[str, Any]:
        run_ref = approval.run_id or approval.task_id
        if not run_ref:
            return {"status": "recorded", "approval_id": approval.approval_id, "resumed": False}
        run = self._find_linked_run(approval)
        if run is None or self.lifecycle.is_terminal(run.status):
            return {"status": "noop", "approval_id": approval.approval_id, "run_id": run_ref, "resumed": False}
        event_type = "approval_denied" if approval.status == "rejected" else "approval_cancelled"
        self.events.create(
            run.run_id,
            event_type,
            "blocked" if approval.status == "rejected" else "cancelled",
            "Approval encerrado sem permitir execucao da acao.",
            metadata={"approval_id": approval.approval_id},
        )
        if approval.status == "rejected":
            if "approval_required" in run.blocked_reasons:
                run.blocked_reasons = [
                    reason for reason in run.blocked_reasons if reason != "approval_required"
                ]
            self.store.update_run(run)
            self.events.create(
                run.run_id,
                "task_cancelled_after_denial",
                run.status,
                "Approval negado; a task sera cancelada sem executar a acao pendente.",
                metadata={"approval_id": approval.approval_id, "operation_type": approval.operation_type},
            )
            cancellation = TaskRunCancellationService(
                store=self.store,
                lifecycle=self.lifecycle,
                events=self.events,
            ).cancel(
                run.run_id,
                TaskCancellationRequest(
                    reason="approval_denied",
                    requested_by=Actor(type="system", id="approval_task_continuation_service"),
                ),
            )
            return {
                "status": "ok",
                "approval_id": approval.approval_id,
                "run_id": run.run_id,
                "run_status": cancellation.status,
                "resumed": False,
                "cancelled": cancellation.cancellation_requested,
            }
        process = self._process_queue_if_enabled()
        return {"status": "ok", "approval_id": approval.approval_id, "run_id": run.run_id, "resumed": False, "queue_process": process}

    def _find_linked_run(self, approval: ApprovalRequest):
        if approval.run_id:
            run = self.store.get_run(approval.run_id)
            if run is not None:
                return run
        if approval.task_id:
            return self.store.get_run_by_task_id(approval.task_id)
        return None

    def _process_queue_if_enabled(self) -> dict[str, Any]:
        try:
            from aipinho.services.runtime.task_runtime_service import TaskRuntimeService

            result = TaskRuntimeService().process_queue()
            return {
                "status": result.get("status"),
                "started_run_id": result.get("started_run_id"),
            }
        except Exception as exc:
            return {"status": "degraded", "reason_code": "queue_process_failed", "error_type": type(exc).__name__}

    def _resume_enabled(self) -> bool:
        lifecycle = self.policy.get("approval_lifecycle", {})
        runtime = self.policy.get("runtime_execution", {})
        return bool(
            isinstance(lifecycle, dict)
            and isinstance(runtime, dict)
            and lifecycle.get("resume_task_after_approval", True)
            and runtime.get("resume_after_approval", True)
            and runtime.get("approved_side_effect_execution_enabled", True)
        )
