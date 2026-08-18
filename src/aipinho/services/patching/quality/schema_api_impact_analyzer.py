from __future__ import annotations

from aipinho.schemas.patching.quality.diff_parse_result import DiffParseResult
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.schemas.patching.quality.schema_api_impact_result import SchemaApiImpactResult


class SchemaApiImpactAnalyzer:
    def analyze(self, parse: DiffParseResult) -> SchemaApiImpactResult:
        schema_files = [path for path in parse.affected_files if "/schemas/" in path.replace("\\", "/")]
        api_files = [path for path in parse.affected_files if "/api/routers/" in path.replace("\\", "/") or path.replace("\\", "/").endswith("_router.py")]
        findings: list[PatchQualityFinding] = []
        if schema_files:
            findings.append(PatchQualityFinding(finding_id="schema_api_schema_1", category="schema_api_impact", severity="medium", message="Alteracao em schema requer teste contratual.", blocking=False, metadata={"files": schema_files}))
        if api_files:
            findings.append(PatchQualityFinding(finding_id="schema_api_router_1", category="schema_api_impact", severity="medium", message="Alteracao em router requer teste de contrato/integracao.", blocking=False, metadata={"files": api_files}))
        return SchemaApiImpactResult(
            status="needs_review" if findings else "ok",
            schema_files_changed=schema_files,
            api_files_changed=api_files,
            requires_contract_tests=bool(schema_files or api_files),
            requires_integration_tests=bool(api_files),
            findings=findings,
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "schema_api_impact_analyzer", "execution_enabled": False}
