from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding


class SyntaxValidationResult(AIpinhoModel):
    status: str = "unknown"
    valid: bool = False
    parser: str = "unknown"
    file_path: str | None = None
    findings: list[PatchQualityFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
