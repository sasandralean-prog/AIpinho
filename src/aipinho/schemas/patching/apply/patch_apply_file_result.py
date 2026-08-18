from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.apply.hunk_apply_result import HunkApplyResult


class PatchApplyFileResult(AIpinhoModel):
    file_path: str
    status: str
    changed: bool = False
    backup_id: str | None = None
    original_hash: str | None = None
    final_hash: str | None = None
    hunk_results: list[HunkApplyResult] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
