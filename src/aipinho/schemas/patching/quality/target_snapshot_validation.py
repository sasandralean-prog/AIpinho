from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding


class TargetSnapshotValidation(AIpinhoModel):
    status: str = "unknown"
    valid: bool = False
    checked_files: int = 0
    matched_hashes: int = 0
    mismatched_hashes: int = 0
    missing_files: int = 0
    findings: list[PatchQualityFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
