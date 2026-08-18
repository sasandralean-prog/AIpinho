from __future__ import annotations

import hashlib
from pathlib import Path

from aipinho.schemas.artifacts.artifact_post_write_validation import ArtifactPostWriteValidation
from aipinho.services.artifacts.artifact_path_guard_service import ArtifactPathGuardService


class ArtifactPostWriteValidator:
    def __init__(self) -> None:
        self.path_guard = ArtifactPathGuardService()

    def validate(self, *, workspace: str, target_path: str, expected_hash: str, expected_bytes: int, temp_path: str, backup_id: str | None = None, overwrite: bool = False) -> ArtifactPostWriteValidation:
        blocked: list[str] = []
        trace: list[str] = ["post_write_validation_started"]
        path = Path(target_path)
        file_exists = path.exists()
        is_file = path.is_file()
        actual_hash = hashlib.sha256(path.read_bytes()).hexdigest() if file_exists and is_file else ""
        size = path.stat().st_size if file_exists and is_file else -1
        target_validation = self.path_guard.validate(workspace, target_path)
        if not file_exists:
            blocked.append("target_missing_after_write")
        if not is_file:
            blocked.append("target_not_file_after_write")
        if actual_hash != expected_hash:
            blocked.append("post_write_hash_mismatch")
        if size != expected_bytes:
            blocked.append("post_write_size_mismatch")
        if not target_validation.valid:
            blocked.extend(target_validation.blocked_reasons)
        if Path(temp_path).exists():
            blocked.append("temp_not_cleaned")
        if overwrite and not backup_id:
            blocked.append("backup_missing_for_overwrite")
        passed = not blocked
        trace.append("post_write_validation_passed" if passed else "post_write_validation_failed")
        return ArtifactPostWriteValidation(
            passed=passed,
            file_exists=file_exists,
            is_file=is_file,
            hash_match=actual_hash == expected_hash,
            size_match=size == expected_bytes,
            target_match=target_validation.valid,
            extension_allowed=target_validation.extension_allowed,
            temp_cleaned=not Path(temp_path).exists(),
            backup_valid=True if backup_id else (None if not overwrite else False),
            blocked_reasons=list(dict.fromkeys(blocked)),
            trace=trace,
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_post_write_validator", "hash_path_size_required": True}
