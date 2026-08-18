from __future__ import annotations

import hashlib
from pathlib import Path

from aipinho.schemas.patching.affected_file import AffectedFile
from aipinho.services.security.secret_guard_service import SecretGuardService


class PatchFileReader:
    def __init__(self) -> None:
        self.secret_guard = SecretGuardService()

    def read(self, affected: AffectedFile) -> tuple[AffectedFile, str]:
        if affected.status == "blocked" or not affected.normalized_path:
            return affected, ""
        path = Path(affected.normalized_path)
        if not path.exists() or not path.is_file():
            affected.status = "allowed"
            affected.original_hash = None
            affected.size_bytes = 0
            affected.warnings.append("target_file_will_be_created")
            return affected, ""
        raw = path.read_bytes()
        try:
            content = raw.decode("utf-8")
        except UnicodeDecodeError:
            affected.status = "blocked"
            affected.blocked_reasons.append("binary_file")
            return affected, ""
        _, secret_warnings = self.secret_guard.redact(content)
        if secret_warnings:
            affected.status = "blocked"
            affected.blocked_reasons.append("secret_file")
            return affected, ""
        affected.original_hash = hashlib.sha256(raw).hexdigest()
        affected.size_bytes = len(raw)
        return affected, content

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_file_reader", "read_only": True}
