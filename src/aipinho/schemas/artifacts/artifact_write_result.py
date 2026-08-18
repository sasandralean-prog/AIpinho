from __future__ import annotations

from pydantic import Field

from aipinho.schemas.artifacts.artifact_post_write_validation import ArtifactPostWriteValidation
from aipinho.schemas.common.base import AIpinhoModel


class ArtifactWriteResult(AIpinhoModel):
    write_run_id: str
    preview_id: str
    approval_id: str
    status: str
    target_path: str
    content_hash: str = ""
    bytes_written: int = 0
    chars_written: int = 0
    backup_id: str | None = None
    post_write_validation: ArtifactPostWriteValidation = Field(default_factory=ArtifactPostWriteValidation)
    safe_to_report_success: bool = False
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    created_at: str
    completed_at: str | None = None
