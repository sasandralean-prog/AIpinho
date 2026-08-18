from __future__ import annotations

from pathlib import Path

from aipinho.schemas.patching.apply.patch_apply_result import PatchApplyResult
from aipinho.schemas.patching.apply.patch_apply_run import PatchApplyRun
from aipinho.schemas.patching.apply.rollback_result import RollbackResult
from aipinho.services.patching.apply.atomic_patch_write_service import AtomicPatchWriteService
from aipinho.services.patching.apply.patch_apply_backup_service import PatchApplyBackupService
from aipinho.services.patching.apply.patch_apply_store import PatchApplyStore


class PatchRollbackService:
    def __init__(self, store: PatchApplyStore | None = None, backup_service: PatchApplyBackupService | None = None, writer: AtomicPatchWriteService | None = None) -> None:
        self.store = store or PatchApplyStore()
        self.backup_service = backup_service or PatchApplyBackupService()
        self.writer = writer or AtomicPatchWriteService()

    def rollback(self, run: PatchApplyRun, result: PatchApplyResult | None = None) -> RollbackResult:
        restored: list[str] = []
        failed: list[str] = []
        for backup_id in run.backup_ids:
            backup = self.backup_service.get_backup(backup_id, run.apply_run_id)
            if backup is None:
                failed.append(backup_id)
                continue
            try:
                source = Path(backup.backup_path)
                self.writer.write(Path(backup.file_path), source.read_text(encoding="utf-8"))
                restored.append(backup.file_path)
            except Exception:
                failed.append(backup.file_path)
        status = "rolled_back" if not failed else "rollback_failed"
        rollback = RollbackResult(status=status, completed=not failed, restored_files=restored, failed_files=failed, manual_review_required=bool(failed))
        if result is not None:
            result.rollback = rollback
            result.status = "failed_with_rollback" if rollback.completed else "rollback_failed"
            result.safe_to_report_success = False
            self.store.save_result(result)
        run.status = rollback.status
        self.store.save_run(run)
        return rollback

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_rollback", "git_enabled": False, "shell_enabled": False}
