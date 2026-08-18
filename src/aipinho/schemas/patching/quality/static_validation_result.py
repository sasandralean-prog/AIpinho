from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.schemas.patching.quality.syntax_validation_result import SyntaxValidationResult


class StaticValidationResult(AIpinhoModel):
    status: str = "unknown"
    valid: bool = False
    checked_files: int = 0
    syntax_results: list[SyntaxValidationResult] = Field(default_factory=list)
    findings: list[PatchQualityFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
