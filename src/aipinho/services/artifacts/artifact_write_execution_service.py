from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_write_policy import ArtifactWritePolicyStatus
from aipinho.schemas.artifacts.artifact_write_request import ArtifactWriteRequest
from aipinho.schemas.artifacts.artifact_write_result import ArtifactWriteResult
from aipinho.schemas.artifacts.artifact_write_run import ArtifactWriteRun
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.artifacts.artifact_atomic_write_service import ArtifactAtomicWriteService
from aipinho.services.artifacts.artifact_backup_service import ArtifactBackupService
from aipinho.services.artifacts.artifact_path_guard_service import ArtifactPathGuardService
from aipinho.services.artifacts.artifact_post_write_validator import ArtifactPostWriteValidator
from aipinho.services.artifacts.artifact_preview_store import ArtifactPreviewStore
from aipinho.services.artifacts.artifact_target_policy_service import ArtifactTargetPolicyService
from aipinho.services.artifacts.artifact_write_event_service import ArtifactWriteEventService
from aipinho.services.artifacts.artifact_write_guard_service import ArtifactWriteGuardService
from aipinho.services.artifacts.artifact_write_lifecycle_service import ArtifactWriteLifecycleService
from aipinho.services.artifacts.artifact_write_store import ArtifactWriteStore
from aipinho.services.session.session_store import utc_now
from aipinho.utils.yaml_loader import inspect_yaml_file, load_yaml_file


class ArtifactWriteExecutionService:
    CONFIGS = [
        "artifact_write_policy.yaml",
        "artifact_write_execution_policy.yaml",
        "artifact_overwrite_policy.yaml",
        "artifact_atomic_write_policy.yaml",
        "artifact_backup_policy.yaml",
        "artifact_post_write_validation_policy.yaml",
        "artifact_write_store_policy.yaml",
        "artifact_write_audit_policy.yaml",
        "artifact_write_lifecycle_policy.yaml",
    ]

    def __init__(
        self,
        preview_store: ArtifactPreviewStore | None = None,
        approval_store: ApprovalStore | None = None,
        write_store: ArtifactWriteStore | None = None,
    ) -> None:
        self.preview_store = preview_store or ArtifactPreviewStore()
        self.approval_store = approval_store or ApprovalStore()
        self.write_store = write_store or ArtifactWriteStore()
        self.guard = ArtifactWriteGuardService(self.preview_store, self.approval_store)
        self.events = ArtifactWriteEventService()
        self.lifecycle = ArtifactWriteLifecycleService()
        self.atomic = ArtifactAtomicWriteService()
        self.backups = ArtifactBackupService()
        self.post_validator = ArtifactPostWriteValidator()
        self.target_policy = ArtifactTargetPolicyService()
        self.path_guard = ArtifactPathGuardService(self.target_policy)
        self.policy = load_yaml_file(PATHS.config_root / "artifacts" / "artifact_write_policy.yaml", critical=True, root=PATHS.config_root / "artifacts")

    def create_run_from_preview(self, preview_id: str, request: ArtifactWriteRequest) -> ArtifactWriteRun:
        if request.preview_id != preview_id:
            raise ValueError("preview_id_mismatch")
        guard = self.guard.validate(request)
        preview = self.preview_store.get_preview(preview_id)
        approval = self.approval_store.get(request.approval_id)
        now = utc_now()
        run = ArtifactWriteRun(
            write_run_id=f"artifact_write_run_{uuid4().hex}",
            preview_id=preview_id,
            approval_id=request.approval_id,
            status="ready_to_execute" if guard.allowed else "blocked",
            workspace=preview.workspace if preview else "",
            target_path=guard.target_path or (preview.target.normalized_target_path if preview and preview.target else ""),
            relative_target_path=preview.target.relative_target_path if preview and preview.target else None,
            content_hash=guard.content_hash,
            preview_status_snapshot=preview.status if preview else "missing",
            approval_status_snapshot=approval.status if approval else "missing",
            approval_scope_snapshot=approval.approval_scope if approval else "missing",
            would_overwrite=guard.would_overwrite,
            allow_overwrite=request.allow_overwrite,
            operator_confirmed=request.operator_confirmed,
            requested_by=request.requested_by,
            created_at=now,
            updated_at=now,
            warnings=guard.warnings,
            blocked_reasons=guard.blocked_reasons,
            trace=guard.trace,
        )
        self.write_store.create_run(run)
        self.write_store.append_event(self.events.event(run.write_run_id, "write_run_created", f"Artifact write run created with status {run.status}.", status=run.status, data={"preview_id": preview_id, "file_written": False}))
        self.write_store.save_trace(run.write_run_id, run.trace)
        return run

    def execute(self, write_run_id: str) -> ArtifactWriteResult:
        run = self.write_store.get_run(write_run_id)
        if run is None:
            raise ValueError("artifact_write_run_not_found")
        existing_result = self.write_store.get_result(write_run_id)
        if existing_result is not None:
            return existing_result
        if run.status != "ready_to_execute":
            result = self._blocked_result(run, [f"write_run_not_ready:{run.status}"])
            self.write_store.save_result(result)
            return result
        request = ArtifactWriteRequest(preview_id=run.preview_id, approval_id=run.approval_id, requested_by=run.requested_by, allow_overwrite=run.allow_overwrite, operator_confirmed=run.operator_confirmed)
        guard = self.guard.validate(request)
        if not guard.allowed or not guard.target_path:
            run.status = "blocked"
            run.blocked_reasons = guard.blocked_reasons
            run.updated_at = utc_now()
            self.write_store.update_run(run)
            result = self._blocked_result(run, guard.blocked_reasons)
            self.write_store.save_result(result)
            self.write_store.append_event(self.events.event(run.write_run_id, "write_blocked", "Artifact write blocked by guard.", status="blocked", data={"blocked_reasons": guard.blocked_reasons}))
            return result
        run.status = "running"
        run.updated_at = utc_now()
        self.write_store.update_run(run)
        self.write_store.append_event(self.events.event(run.write_run_id, "write_started", "Artifact write execution started.", data={"target_path": guard.target_path, "content_hash": guard.content_hash}))
        backup_id = None
        try:
            if Path(guard.target_path).exists():
                backup = self.backups.create_backup(guard.target_path, run.write_run_id)
                backup_id = backup.backup_id
                run.backup_id = backup_id
                self.write_store.append_event(self.events.event(run.write_run_id, "backup_created", "Internal backup created before overwrite.", data={"backup_id": backup_id, "target_path": guard.target_path}))
            atomic_result = self.atomic.write_text_atomic(guard.target_path, guard.resolved_content, overwrite=run.allow_overwrite)
            if atomic_result.status != "completed":
                run.status = "failed"
                run.updated_at = utc_now()
                self.write_store.update_run(run)
                result = self._failed_result(run, atomic_result.blocked_reasons, backup_id=backup_id)
                self.write_store.save_result(result)
                return result
            validation = self.post_validator.validate(
                workspace=run.workspace,
                target_path=guard.target_path,
                expected_hash=guard.content_hash,
                expected_bytes=atomic_result.bytes_written,
                temp_path=atomic_result.temp_path,
                backup_id=backup_id,
                overwrite=run.would_overwrite,
            )
            run.status = "completed" if validation.passed else "failed"
            run.backup_id = backup_id
            run.updated_at = utc_now()
            self.write_store.update_run(run)
            result = ArtifactWriteResult(
                write_run_id=run.write_run_id,
                preview_id=run.preview_id,
                approval_id=run.approval_id,
                status=run.status,
                target_path=guard.target_path,
                content_hash=guard.content_hash,
                bytes_written=atomic_result.bytes_written,
                chars_written=atomic_result.chars_written,
                backup_id=backup_id,
                post_write_validation=validation,
                safe_to_report_success=validation.passed,
                warnings=validation.warnings,
                blocked_reasons=validation.blocked_reasons,
                created_at=run.created_at,
                completed_at=utc_now(),
            )
            self.write_store.save_result(result)
            self.write_store.append_event(self.events.event(run.write_run_id, "post_validation_passed" if validation.passed else "post_validation_failed", "Post-write validation finished.", status=result.status, data={"passed": validation.passed}))
            self.write_store.append_event(self.events.event(run.write_run_id, "write_completed" if validation.passed else "write_failed", "Artifact write finished.", status=result.status, data={"safe_to_report_success": result.safe_to_report_success}))
            return result
        except Exception as exc:
            if backup_id:
                try:
                    self.backups.restore_backup(backup_id, guard.target_path)
                except Exception:
                    pass
            run.status = "failed"
            run.backup_id = backup_id
            run.updated_at = utc_now()
            self.write_store.update_run(run)
            result = self._failed_result(run, [str(exc)], backup_id=backup_id)
            self.write_store.save_result(result)
            self.write_store.append_event(self.events.event(run.write_run_id, "write_failed", "Artifact write failed safely.", status="failed", data={"error": str(exc), "backup_id": backup_id or ""}))
            return result

    def cancel(self, write_run_id: str) -> ArtifactWriteRun:
        run = self.write_store.get_run(write_run_id)
        if run is None:
            raise ValueError("artifact_write_run_not_found")
        if self.lifecycle.is_terminal(run.status) or run.status == "running":
            raise ValueError("artifact_write_run_not_cancellable")
        run.status = "cancelled"
        run.updated_at = utc_now()
        self.write_store.update_run(run)
        self.write_store.append_event(self.events.event(run.write_run_id, "write_cancelled", "Artifact write run cancelled before execution.", status="cancelled"))
        return run

    def get_run(self, write_run_id: str) -> ArtifactWriteRun | None:
        return self.write_store.get_run(write_run_id)

    def get_result(self, write_run_id: str) -> ArtifactWriteResult | None:
        return self.write_store.get_result(write_run_id)

    def get_events(self, write_run_id: str):
        return self.write_store.get_events(write_run_id)

    def get_trace(self, write_run_id: str):
        return self.write_store.get_trace(write_run_id)

    def list_runs(self, **filters):
        return self.write_store.list_runs(**filters)

    def status(self) -> ArtifactWritePolicyStatus:
        statuses = [inspect_yaml_file(PATHS.config_root / "artifacts" / name, root=PATHS.config_root / "artifacts") for name in self.CONFIGS]
        warnings = [f"{status.path}:{status.status}" for status in statuses if status.status != "ok"]
        settings = self.policy.get("artifact_write", {}) if isinstance(self.policy.get("artifact_write"), dict) else {}
        return ArtifactWritePolicyStatus(
            status="degraded" if warnings else "ok",
            enabled=bool(settings.get("enabled", True)),
            mode=str(settings.get("mode", "approved_non_code_writes")),
            direct_payload_write_enabled=bool(settings.get("allow_direct_payload_write", False)),
            source_code_write_enabled=False,
            active_config_write_enabled=False,
            script_write_enabled=False,
            approved_preview_required=bool(settings.get("require_preview_approved", True)),
            approval_required=bool(settings.get("require_approval", True)),
            hash_lock_required=bool(settings.get("require_hash_lock", True)),
            target_lock_required=bool(settings.get("require_target_lock", True)),
            post_write_validation_required=bool(settings.get("require_post_write_validation", True)),
            allowed_extensions=self.target_policy.allowed_extensions(),
            allowed_base_dirs=self.target_policy.allowed_base_dirs(),
            warnings=warnings,
        )

    def _blocked_result(self, run: ArtifactWriteRun, blocked_reasons: list[str]) -> ArtifactWriteResult:
        return ArtifactWriteResult(
            write_run_id=run.write_run_id,
            preview_id=run.preview_id,
            approval_id=run.approval_id,
            status="blocked",
            target_path=run.target_path,
            content_hash=run.content_hash,
            safe_to_report_success=False,
            blocked_reasons=list(dict.fromkeys(blocked_reasons)),
            created_at=run.created_at,
            completed_at=utc_now(),
        )

    def _failed_result(self, run: ArtifactWriteRun, blocked_reasons: list[str], *, backup_id: str | None = None) -> ArtifactWriteResult:
        return ArtifactWriteResult(
            write_run_id=run.write_run_id,
            preview_id=run.preview_id,
            approval_id=run.approval_id,
            status="failed",
            target_path=run.target_path,
            content_hash=run.content_hash,
            backup_id=backup_id,
            safe_to_report_success=False,
            blocked_reasons=list(dict.fromkeys(blocked_reasons)),
            created_at=run.created_at,
            completed_at=utc_now(),
        )
