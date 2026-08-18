from __future__ import annotations

from aipinho.schemas.common.base import AIpinhoModel


class PatchApplyBackup(AIpinhoModel):
    backup_id: str
    apply_run_id: str
    file_path: str
    backup_path: str
    original_hash: str
    size_bytes: int = 0
    created_at: str
    valid: bool = True
