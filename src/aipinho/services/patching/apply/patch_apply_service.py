from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.patching.apply.patch_apply_request import PatchApplyRequest
from aipinho.schemas.patching.apply.patch_apply_result import PatchApplyResult
from aipinho.schemas.patching.apply.patch_apply_run import PatchApplyRun
from aipinho.schemas.patching.apply.patch_apply_status import PatchApplyStatus
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.patching.apply.patch_apply_approval_bridge import PatchApplyApprovalBridge
from aipinho.services.patching.apply.patch_apply_audit_service import PatchApplyAuditService
from aipinho.services.patching.apply.patch_apply_engine import PatchApplyEngine
from aipinho.services.patching.apply.patch_apply_event_service import PatchApplyEventService
from aipinho.services.patching.apply.patch_apply_guard_service import PatchApplyGuardService
from aipinho.services.patching.apply.patch_apply_lifecycle_service import PatchApplyLifecycleService
from aipinho.services.patching.apply.patch_apply_store import PatchApplyStore
from aipinho.services.patching.apply.patch_apply_trace_service import PatchApplyTraceService
from aipinho.services.patching.apply.patch_rollback_service import PatchRollbackService
from aipinho.services.patching.apply.post_apply_validator import PostApplyValidator
from aipinho.services.patching.apply.workspace_mutation_tracker import WorkspaceMutationTracker
from aipinho.services.patching.patch_plan_store import PatchPlanStore
from aipinho.services.patching.quality.patch_quality_gate_service import PatchQualityGateService
from aipinho.services.session.session_store import utc_now
from aipinho.utils.yaml_loader import inspect_yaml_file
from aipinho.core.paths import PATHS


class PatchApplyService:
    CONFIGS = [
        "patch_apply_policy.yaml",
        "patch_apply_execution_policy.yaml",
        "patch_apply_guard_policy.yaml",
        "patch_apply_approval_policy.yaml",
        "patch_apply_backup_policy.yaml",
        "patch_apply_atomic_write_policy.yaml",
        "post_apply_validation_policy.yaml",
        "patch_apply_store_policy.yaml",
        "patch_apply_audit_policy.yaml",
        "patch_apply_lifecycle_policy.yaml",
        "patch_rollback_policy.yaml",
        "workspace_mutation_tracking_policy.yaml",
    ]

    def __init__(self, store: PatchApplyStore | None = None, plan_store: PatchPlanStore | None = None) -> None:
        self.store = store or PatchApplyStore()
        self.plan_store = plan_store or PatchPlanStore()
        self.quality = PatchQualityGateService(plan_store=self.plan_store)
        self.approval_service = ApprovalService()
        self.approval_bridge = PatchApplyApprovalBridge(plan_store=self.plan_store, approval_store=self.approval_service.store, quality_service=self.quality)
        self.guard = PatchApplyGuardService()
        self.lifecycle = PatchApplyLifecycleService()
        self.events = PatchApplyEventService()
        self.trace_service = PatchApplyTraceService()
        self.engine = PatchApplyEngine()
        self.post_validator = PostApplyValidator()
        self.rollback_service = PatchRollbackService(store=self.store)
        self.audit = PatchApplyAuditService()

    def request_approval(self, plan_id: str):
        return self.approval_bridge.request_approval(plan_id)

    def create_run_from_plan(self, plan_id: str, request: PatchApplyRequest) -> PatchApplyRun:
        plan = self.plan_store.get_plan(plan_id)
        quality = self.quality.get_latest_for_plan(plan_id) if plan else None
        guard = self.guard.validate(plan, quality, request, approval_service=self.approval_service)
        now = utc_now()
        run = PatchApplyRun(
            apply_run_id=f"patch_apply_run_{uuid4().hex}",
            plan_id=plan_id,
            quality_id=quality.quality_id if quality else "",
            approval_id=request.approval_id or "",
            status="ready_to_execute" if guard.allowed else "blocked",
            workspace=plan.workspace if plan else "",
            operator_confirmed=request.operator_confirmed,
            diff_hash=guard.diff_hash or "",
            target_files=guard.target_files,
            original_hashes={file.relative_path or file.path: file.original_hash or "" for file in plan.affected_files} if plan else {},
            guard=guard,
            created_at=now,
            updated_at=now,
            blocked_reasons=guard.blocking_reasons,
            warnings=guard.warnings,
            trace=["patch_apply_run_created_without_execution"],
        )
        self.store.save_run(run)
        self.store.append_event(self.events.create(run.apply_run_id, "apply_run_created", f"PatchApplyRun created with status {run.status}.", {"plan_id": plan_id, "applied": False}))
        self.store.save_trace(self.trace_service.create(run.apply_run_id))
        return run

    def execute(self, apply_run_id: str) -> PatchApplyResult | None:
        run = self.store.get_run(apply_run_id)
        if run is None:
            return None
        existing = self.store.get_result(apply_run_id)
        if existing is not None:
            return existing
        if not self.lifecycle.can_execute(run.status):
            return self._blocked_result(run, [f"run_not_ready:{run.status}"])
        plan = self.plan_store.get_plan(run.plan_id)
        quality = self.quality.get_latest_for_plan(run.plan_id) if plan else None
        request = PatchApplyRequest(approval_id=run.approval_id, operator_confirmed=run.operator_confirmed)
        guard = self.guard.validate(plan, quality, request, approval_service=self.approval_service)
        run.guard = guard
        if not guard.allowed or plan is None:
            run.status = "blocked"
            run.blocked_reasons = guard.blocking_reasons
            run.updated_at = utc_now()
            self.store.save_run(run)
            return self._blocked_result(run, guard.blocking_reasons)
        run.status = "running"
        run.updated_at = utc_now()
        self.store.save_run(run)
        self.store.append_event(self.events.create(run.apply_run_id, "apply_started", "Patch apply started through explicit execute endpoint."))
        tracker = WorkspaceMutationTracker([file.normalized_path or "" for file in plan.affected_files])
        file_results = []
        try:
            file_results = self.engine.apply(plan, run.apply_run_id, tracker)
            run.backup_ids = [item.backup_id for item in file_results if item.backup_id]
            post = self.post_validator.validate(plan, run.apply_run_id, file_results, tracker)
            status = "completed" if post.passed else "failed"
            result = PatchApplyResult(apply_run_id=run.apply_run_id, plan_id=run.plan_id, status=status, safe_to_report_success=post.passed, files=file_results, post_apply_validation=post, created_at=utc_now(), updated_at=utc_now())
            if not post.passed:
                self.rollback_service.rollback(run, result)
            else:
                run.status = "completed"
                run.result_id = run.apply_run_id
                run.updated_at = utc_now()
                self.store.save_run(run)
                self.store.append_event(self.events.create(run.apply_run_id, "post_validation_passed", "Post-apply validation passed."))
                self.store.save_result(result)
            self.audit.audit(run, result)
            return self.store.get_result(run.apply_run_id) or result
        except Exception as exc:
            result = PatchApplyResult(apply_run_id=run.apply_run_id, plan_id=run.plan_id, status="failed", safe_to_report_success=False, files=file_results, blocked_reasons=[str(exc)], created_at=utc_now(), updated_at=utc_now())
            self.rollback_service.rollback(run, result)
            self.store.save_result(result)
            return result

    def cancel(self, apply_run_id: str) -> PatchApplyRun | None:
        run = self.store.get_run(apply_run_id)
        if run is None:
            return None
        if self.lifecycle.can_cancel(run.status):
            run.status = "cancelled"
            run.updated_at = utc_now()
            self.store.save_run(run)
            self.store.append_event(self.events.create(run.apply_run_id, "apply_cancelled", "PatchApplyRun cancelled before execution."))
        return run

    def rollback(self, apply_run_id: str):
        run = self.store.get_run(apply_run_id)
        if run is None:
            return None
        result = self.store.get_result(apply_run_id)
        return self.rollback_service.rollback(run, result)

    def get_run(self, apply_run_id: str) -> PatchApplyRun | None:
        return self.store.get_run(apply_run_id)

    def get_events(self, apply_run_id: str):
        return self.store.get_events(apply_run_id)

    def get_trace(self, apply_run_id: str):
        return self.store.get_trace(apply_run_id)

    def get_result(self, apply_run_id: str):
        return self.store.get_result(apply_run_id)

    def list_runs(self, **filters):
        return self.store.list_runs(**filters)

    def apply_status_for_plan(self, plan_id: str) -> dict[str, object]:
        runs = self.store.list_runs(plan_id=plan_id, limit=10)
        quality = self.quality.get_latest_for_plan(plan_id)
        return {
            "status": "ok",
            "plan_id": plan_id,
            "quality_status": quality.status if quality else "missing",
            "latest_apply_run": runs[0].model_dump() if runs else None,
            "can_create_apply_run": bool(quality and quality.status == "passed"),
            "blocking_reasons": [] if quality and quality.status == "passed" else ["patch_quality_not_passed_or_missing"],
        }

    def _blocked_result(self, run: PatchApplyRun, reasons: list[str]) -> PatchApplyResult:
        result = PatchApplyResult(apply_run_id=run.apply_run_id, plan_id=run.plan_id, status="blocked", safe_to_report_success=False, blocked_reasons=list(dict.fromkeys(reasons)), created_at=utc_now(), updated_at=utc_now())
        self.store.save_result(result)
        self.store.append_event(self.events.create(run.apply_run_id, "apply_blocked", "Patch apply blocked by guard.", {"reasons": reasons}))
        return result

    def status(self) -> PatchApplyStatus:
        root = PATHS.config_root / "patching" / "apply"
        statuses = [inspect_yaml_file(root / name, root=root) for name in self.CONFIGS]
        warnings = [f"{item.path}:{item.status}" for item in statuses if item.status != "ok"]
        return PatchApplyStatus(status="degraded" if warnings else "ok", warnings=warnings)
