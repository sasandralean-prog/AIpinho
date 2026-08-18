from __future__ import annotations

from pathlib import Path

from aipinho.schemas.patching.apply.patch_apply_file_result import PatchApplyFileResult
from aipinho.schemas.patching.apply.post_apply_validation import PostApplyValidation
from aipinho.schemas.patching.patch_plan import PatchPlan
from aipinho.services.patching.apply.patch_apply_backup_service import PatchApplyBackupService
from aipinho.services.patching.apply.patch_apply_hashing import sha256_file
from aipinho.services.patching.apply.workspace_mutation_tracker import WorkspaceMutationTracker
from aipinho.services.patching.quality.static_syntax_validator import StaticSyntaxValidator


class PostApplyValidator:
    def __init__(self, backup_service: PatchApplyBackupService | None = None, syntax_validator: StaticSyntaxValidator | None = None) -> None:
        self.backup_service = backup_service or PatchApplyBackupService()
        self.syntax_validator = syntax_validator or StaticSyntaxValidator()

    def validate(self, plan: PatchPlan, apply_run_id: str, file_results: list[PatchApplyFileResult], tracker: WorkspaceMutationTracker) -> PostApplyValidation:
        blocking: list[str] = []
        warnings: list[str] = []
        final_hashes: dict[str, str] = {}
        proposed_contents: dict[str, str] = {}
        checked_files: list[str] = []
        for result in file_results:
            path = self._target_path(plan, result.file_path)
            if path is None or not path.exists():
                blocking.append(f"target_missing_after_apply:{result.file_path}")
                continue
            checked_files.append(result.file_path)
            final_hash = sha256_file(path)
            final_hashes[result.file_path] = final_hash
            if result.final_hash and final_hash != result.final_hash:
                blocking.append(f"final_hash_mismatch:{result.file_path}")
            if result.backup_id:
                backup = self.backup_service.get_backup(result.backup_id, apply_run_id)
                if backup is None or not self.backup_service.validate_backup(backup):
                    blocking.append(f"backup_missing_or_invalid:{result.file_path}")
            elif not self._is_create_file_result(plan, result):
                blocking.append(f"backup_missing:{result.file_path}")
            proposed_contents[result.file_path] = path.read_text(encoding="utf-8")
            if not all(hunk.applied for hunk in result.hunk_results):
                blocking.append(f"hunk_not_applied:{result.file_path}")
        reconciliation = tracker.reconcile()
        blocking.extend(reconciliation.unexpected_writes)
        blocking.extend([f"temp_leftover:{path}" for path in reconciliation.temp_files])
        syntax = self.syntax_validator.validate(proposed_contents)
        if not syntax.valid:
            blocking.append("static_syntax_validation_failed")
        warnings.extend(syntax.warnings)
        passed = not blocking and all(result.status == "completed" for result in file_results)
        return PostApplyValidation(status="passed" if passed else "failed", passed=passed, final_hashes=final_hashes, checked_files=checked_files, unexpected_writes=reconciliation.unexpected_writes, temp_files_remaining=reconciliation.temp_files, warnings=warnings, blocking_reasons=list(dict.fromkeys(blocking)))

    def _target_path(self, plan: PatchPlan, rel: str) -> Path | None:
        for affected in plan.affected_files:
            if rel in {affected.relative_path, affected.path}:
                return Path(affected.normalized_path or "")
        return None

    def _is_create_file_result(self, plan: PatchPlan, result: PatchApplyFileResult) -> bool:
        normalized = result.file_path.replace("\\", "/")
        affected = next((item for item in plan.affected_files if (item.relative_path or item.path).replace("\\", "/") == normalized), None)
        if affected is not None and affected.original_hash:
            return False
        hunks = [hunk for hunk in plan.hunks if hunk.file_path.replace("\\", "/") == normalized]
        return bool(hunks) and all(hunk.original == "" for hunk in hunks) and "created_new_file" in result.warnings

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "post_apply_validator", "run_tests": False, "shell": False}
