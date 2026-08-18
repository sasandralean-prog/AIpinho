from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding


class SchemaApiImpactResult(AIpinhoModel):
    status: str = "unknown"
    schema_files_changed: list[str] = Field(default_factory=list)
    api_files_changed: list[str] = Field(default_factory=list)
    requires_contract_tests: bool = False
    requires_integration_tests: bool = False
    findings: list[PatchQualityFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
