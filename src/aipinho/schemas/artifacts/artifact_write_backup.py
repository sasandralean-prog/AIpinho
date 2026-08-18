from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class ArtifactWriteBackup(AIpinhoModel):
    backup_id: str
    write_run_id: str
    original_path: str
    backup_path: str
    original_hash: str
    original_size_bytes: int = 0
    created_at: str
    status: str = "created"
    warnings: list[str] = Field(default_factory=list)
