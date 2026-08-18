from __future__ import annotations

from aipinho.schemas.patching.diff_proposal import DiffProposal
from aipinho.schemas.patching.patch_plan import PatchPlan
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.schemas.patching.quality.schema_api_impact_result import SchemaApiImpactResult
from aipinho.schemas.patching.quality.test_plan_validation_result import TestPlanValidationResult


class TestPlanValidator:
    def validate(self, plan: PatchPlan | None, diff: DiffProposal | None, schema_api_impact: SchemaApiImpactResult) -> TestPlanValidationResult:
        recommended = [item.test_type for item in plan.test_recommendations] if plan else []
        affected = [file.relative_path or file.path for file in plan.affected_files] if plan else []
        missing: list[str] = []
        if any(path.endswith(".py") for path in affected) and "py_compile" not in recommended:
            missing.append("py_compile")
        if schema_api_impact.requires_contract_tests and "contract" not in recommended:
            missing.append("contract")
        if schema_api_impact.requires_integration_tests and "integration" not in recommended:
            missing.append("integration")
        if diff is not None and not recommended:
            missing.append("focused_review")
        findings = [
            PatchQualityFinding(finding_id=f"test_plan_missing_{index}", category="test_plan", severity="medium", message=f"Plano de teste recomendado ausente: {item}", blocking=False)
            for index, item in enumerate(missing, start=1)
        ]
        return TestPlanValidationResult(status="needs_review" if missing else "ok", valid=not missing, recommended_tests=recommended, missing_test_types=missing, findings=findings)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "test_plan_validator", "execution_enabled": False}
