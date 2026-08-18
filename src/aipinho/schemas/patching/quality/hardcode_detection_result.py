from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding


class HardcodeDetectionResult(AIpinhoModel):
    status: str = "unknown"
    hardcodes_found: int = 0
    critical_found: int = 0
    findings: list[PatchQualityFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
