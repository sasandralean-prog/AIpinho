from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


class PatchApplyGuardResult(AIpinhoModel):
    status: str = "unknown"
    allowed: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    plan_id: str | None = None
    quality_id: str | None = None
    approval_id: str | None = None
    diff_hash: str | None = None
    target_files: list[str] = Field(default_factory=list)
