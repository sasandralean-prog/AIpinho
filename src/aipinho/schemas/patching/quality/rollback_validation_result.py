from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding


class RollbackValidationResult(AIpinhoModel):
    status: str = "unknown"
    valid: bool = False
    notes_checked: int = 0
    automatic_rollback_enabled: bool = False
    findings: list[PatchQualityFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
