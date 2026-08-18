from __future__ import annotations

from aipinho.schemas.patching.patch_plan import PatchPlan
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.schemas.patching.quality.rollback_validation_result import RollbackValidationResult


class RollbackNoteValidator:
    def validate(self, plan: PatchPlan | None) -> RollbackValidationResult:
        if plan is None:
            return RollbackValidationResult(status="not_applicable", valid=True)
        notes_by_file = {note.file_path: note for note in plan.rollback_notes}
        findings: list[PatchQualityFinding] = []
        automatic = False
        for index, affected in enumerate(plan.affected_files, start=1):
            file_key = affected.relative_path or affected.path
            note = notes_by_file.get(file_key) or notes_by_file.get(affected.path)
            if note is None:
                findings.append(PatchQualityFinding(finding_id=f"rollback_missing_{index}", category="rollback", severity="high", message="Arquivo afetado sem rollback note.", file_path=file_key, blocking=True))
                continue
            if not note.original_hash and "target_file_will_be_created" not in affected.warnings:
                findings.append(PatchQualityFinding(finding_id=f"rollback_hash_missing_{index}", category="rollback", severity="medium", message="Rollback note sem hash original.", file_path=file_key, blocking=False))
            if note.automatic_rollback_enabled:
                automatic = True
                findings.append(PatchQualityFinding(finding_id=f"rollback_auto_{index}", category="rollback", severity="high", message="Rollback automatico nao e permitido nesta fase.", file_path=file_key, blocking=True))
        valid = not any(item.blocking for item in findings)
        return RollbackValidationResult(status="ok" if valid and not findings else ("failed" if not valid else "needs_review"), valid=valid, notes_checked=len(plan.rollback_notes), automatic_rollback_enabled=automatic, findings=findings)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "rollback_note_validator", "execution_enabled": False}
