from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.patching.apply.patch_apply_backup import PatchApplyBackup
from aipinho.services.patching.apply.patch_apply_hashing import sha256_file
from aipinho.services.security.secret_guard_service import SecretGuardService
from aipinho.services.session.session_store import utc_now
from aipinho.utils.safe_paths import resolve_within_root
from aipinho.utils.yaml_loader import load_yaml_file


class PatchApplyBackupService:
    def __init__(self, root: Path | None = None) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "patching" / "apply" / "patch_apply_backup_policy.yaml", critical=True, root=PATHS.config_root / "patching" / "apply")
        configured = str((self.policy.get("backup", {}) or {}).get("location", "data/runtime/patch_backups"))
        self.root = root or resolve_within_root(PATHS.project_root / configured, PATHS.project_root)
        self.secret_guard = SecretGuardService()

    def create_backup(self, file_path: Path, apply_run_id: str) -> PatchApplyBackup:
        if not file_path.exists() or not file_path.is_file():
            raise ValueError("backup_target_missing")
        content = file_path.read_text(encoding="utf-8")
        _, warnings = self.secret_guard.redact(content)
        if warnings:
            raise ValueError("backup_secret_file_blocked")
        backup_id = f"patch_backup_{uuid4().hex}"
        backup_dir = resolve_within_root(self.root / apply_run_id, self.root)
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup_path = resolve_within_root(backup_dir / f"{backup_id}.txt", self.root)
        backup_path.write_text(content, encoding="utf-8")
        backup = PatchApplyBackup(
            backup_id=backup_id,
            apply_run_id=apply_run_id,
            file_path=str(file_path),
            backup_path=str(backup_path),
            original_hash=sha256_file(file_path),
            size_bytes=backup_path.stat().st_size,
            created_at=utc_now(),
        )
        (backup_dir / f"{backup_id}.json").write_text(json.dumps(backup.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
        return backup

    def get_backup(self, backup_id: str, apply_run_id: str) -> PatchApplyBackup | None:
        path = self.root / apply_run_id / f"{backup_id}.json"
        if not path.exists():
            return None
        return PatchApplyBackup.model_validate(json.loads(path.read_text(encoding="utf-8-sig")))

    def restore_backup(self, backup: PatchApplyBackup, target_path: Path) -> None:
        source = resolve_within_root(Path(backup.backup_path), self.root)
        target_path.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")

    def validate_backup(self, backup: PatchApplyBackup) -> bool:
        path = Path(backup.backup_path)
        return path.exists() and path.is_file() and path.stat().st_size == backup.size_bytes

    def status(self) -> dict[str, object]:
        self.root.mkdir(parents=True, exist_ok=True)
        return {"status": "ok", "service": "patch_apply_backup", "path": str(self.root)}
