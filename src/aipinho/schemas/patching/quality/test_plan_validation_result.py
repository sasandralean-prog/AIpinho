from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding


class TestPlanValidationResult(AIpinhoModel):
    status: str = "unknown"
    valid: bool = False
    recommended_tests: list[str] = Field(default_factory=list)
    missing_test_types: list[str] = Field(default_factory=list)
    findings: list[PatchQualityFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
