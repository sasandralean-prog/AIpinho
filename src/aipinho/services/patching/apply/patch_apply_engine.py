from __future__ import annotations

from pathlib import Path

from aipinho.schemas.patching.apply.patch_apply_file_result import PatchApplyFileResult
from aipinho.schemas.patching.patch_plan import PatchPlan
from aipinho.services.patching.apply.atomic_patch_write_service import AtomicPatchWriteService
from aipinho.services.patching.apply.hunk_apply_engine import HunkApplyEngine
from aipinho.services.patching.apply.patch_apply_backup_service import PatchApplyBackupService
from aipinho.services.patching.apply.patch_apply_hashing import sha256_file, sha256_text
from aipinho.services.patching.apply.workspace_mutation_tracker import WorkspaceMutationTracker


class PatchApplyEngine:
    def __init__(self, backup_service: PatchApplyBackupService | None = None, writer: AtomicPatchWriteService | None = None, hunk_engine: HunkApplyEngine | None = None) -> None:
        self.backup_service = backup_service or PatchApplyBackupService()
        self.writer = writer or AtomicPatchWriteService()
        self.hunk_engine = hunk_engine or HunkApplyEngine()

    def apply(self, plan: PatchPlan, apply_run_id: str, tracker: WorkspaceMutationTracker) -> list[PatchApplyFileResult]:
        results: list[PatchApplyFileResult] = []
        hunks_by_file: dict[str, list] = {}
        for hunk in plan.hunks:
            hunks_by_file.setdefault(self._path_key(hunk.file_path), []).append(hunk)
        for affected in plan.affected_files:
            rel = affected.relative_path or affected.path
            path = Path(affected.normalized_path or "")
            existed_before = path.exists()
            original_hash = sha256_file(path) if existed_before else sha256_text("")
            backup = self.backup_service.create_backup(path, apply_run_id) if existed_before else None
            content = path.read_text(encoding="utf-8") if existed_before else ""
            hunk_results = []
            updated = content
            for hunk in hunks_by_file.get(self._path_key(rel), []):
                updated, hunk_result = self.hunk_engine.apply(updated, hunk)
                hunk_results.append(hunk_result)
                if not hunk_result.applied:
                    results.append(PatchApplyFileResult(file_path=rel, status="failed", changed=False, backup_id=backup.backup_id if backup else None, original_hash=original_hash, final_hash=original_hash, hunk_results=hunk_results, blocked_reasons=[hunk_result.reason]))
                    return results
            final_hash = self.writer.write(path, updated)
            tracker.record_write(path)
            results.append(PatchApplyFileResult(file_path=rel, status="completed", changed=final_hash != original_hash, backup_id=backup.backup_id if backup else None, original_hash=original_hash, final_hash=final_hash, hunk_results=hunk_results, warnings=[] if existed_before else ["created_new_file"]))
        return results

    def _path_key(self, path: str) -> str:
        return path.replace("\\", "/").strip("/")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_apply_engine", "shell_enabled": False, "git_enabled": False}
