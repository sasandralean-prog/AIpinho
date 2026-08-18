from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_write_backup import ArtifactWriteBackup
from aipinho.services.artifacts.artifact_secret_scanner import ArtifactSecretScanner
from aipinho.services.session.session_store import utc_now
from aipinho.utils.safe_paths import resolve_within_root
from aipinho.utils.yaml_loader import load_yaml_file


class ArtifactBackupService:
    def __init__(self, root: Path | None = None) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "artifacts" / "artifact_backup_policy.yaml", critical=True, root=PATHS.config_root / "artifacts")
        configured = str((self.policy.get("backup", {}) or {}).get("location", "data/runtime/artifact_backups"))
        self.root = root or resolve_within_root(PATHS.project_root / configured, PATHS.project_root)
        self.secret_scanner = ArtifactSecretScanner()

    def create_backup(self, existing_target_path: str, write_run_id: str) -> ArtifactWriteBackup:
        target = Path(existing_target_path)
        if not target.exists() or not target.is_file():
            raise ValueError("backup_target_missing")
        raw = target.read_bytes()
        max_bytes = int((self.policy.get("backup", {}) or {}).get("max_backup_bytes", 300000))
        if len(raw) > max_bytes:
            raise ValueError("backup_size_limit_exceeded")
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("backup_binary_blocked") from exc
        if self.secret_scanner.has_secret(text):
            raise ValueError("backup_secret_file_blocked")
        backup_id = f"artifact_backup_{uuid4().hex}"
        backup_path = resolve_within_root(self.root / f"{backup_id}.txt", self.root)
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        backup_path.write_text(self.secret_scanner.redact(text), encoding="utf-8")
        return ArtifactWriteBackup(
            backup_id=backup_id,
            write_run_id=write_run_id,
            original_path=str(target),
            backup_path=str(backup_path),
            original_hash=hashlib.sha256(raw).hexdigest(),
            original_size_bytes=len(raw),
            created_at=utc_now(),
        )

    def restore_backup(self, backup_id: str, target_path: str) -> bool:
        backup_path = resolve_within_root(self.root / f"{backup_id}.txt", self.root)
        if not backup_path.exists():
            return False
        Path(target_path).write_text(backup_path.read_text(encoding="utf-8"), encoding="utf-8")
        return True

    def status(self) -> dict[str, object]:
        self.root.mkdir(parents=True, exist_ok=True)
        return {"status": "ok", "service": "artifact_backup", "path": str(self.root), "workspace_bak_files": False}
