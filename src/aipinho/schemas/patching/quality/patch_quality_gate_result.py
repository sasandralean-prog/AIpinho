from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.patching.quality.diff_parse_result import DiffParseResult
from aipinho.schemas.patching.quality.hardcode_detection_result import HardcodeDetectionResult
from aipinho.schemas.patching.quality.hunk_validation_result import HunkValidationResult
from aipinho.schemas.patching.quality.import_impact_result import ImportImpactResult
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.schemas.patching.quality.patch_quality_score import PatchQualityScore
from aipinho.schemas.patching.quality.patch_quality_trace import PatchQualityTrace
from aipinho.schemas.patching.quality.policy_bypass_detection_result import PolicyBypassDetectionResult
from aipinho.schemas.patching.quality.rollback_validation_result import RollbackValidationResult
from aipinho.schemas.patching.quality.schema_api_impact_result import SchemaApiImpactResult
from aipinho.schemas.patching.quality.security_regression_result import SecurityRegressionResult
from aipinho.schemas.patching.quality.static_validation_result import StaticValidationResult
from aipinho.schemas.patching.quality.target_snapshot_validation import TargetSnapshotValidation
from aipinho.schemas.patching.quality.test_plan_validation_result import TestPlanValidationResult


class PatchQualityGateResult(AIpinhoModel):
    quality_id: str
    plan_id: str | None = None
    status: str
    score: PatchQualityScore = Field(default_factory=PatchQualityScore)
    safe_for_future_apply_review: bool = False
    apply_enabled: bool = False
    write_enabled: bool = False
    shell_enabled: bool = False
    git_enabled: bool = False
    test_execution_enabled: bool = False
    diff_parse: DiffParseResult = Field(default_factory=DiffParseResult)
    hunk_validation: HunkValidationResult = Field(default_factory=HunkValidationResult)
    target_snapshot_validation: TargetSnapshotValidation = Field(default_factory=TargetSnapshotValidation)
    static_validation: StaticValidationResult = Field(default_factory=StaticValidationResult)
    hardcode_detection: HardcodeDetectionResult = Field(default_factory=HardcodeDetectionResult)
    policy_bypass_detection: PolicyBypassDetectionResult = Field(default_factory=PolicyBypassDetectionResult)
    security_regression: SecurityRegressionResult = Field(default_factory=SecurityRegressionResult)
    import_impact: ImportImpactResult = Field(default_factory=ImportImpactResult)
    schema_api_impact: SchemaApiImpactResult = Field(default_factory=SchemaApiImpactResult)
    test_plan_validation: TestPlanValidationResult = Field(default_factory=TestPlanValidationResult)
    rollback_validation: RollbackValidationResult = Field(default_factory=RollbackValidationResult)
    findings: list[PatchQualityFinding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: PatchQualityTrace | None = None
    created_at: str
    updated_at: str
