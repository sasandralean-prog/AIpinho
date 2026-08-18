from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding


class ImportImpactResult(AIpinhoModel):
    status: str = "unknown"
    changed_imports: list[str] = Field(default_factory=list)
    risky_imports: list[str] = Field(default_factory=list)
    requires_review: bool = False
    findings: list[PatchQualityFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
