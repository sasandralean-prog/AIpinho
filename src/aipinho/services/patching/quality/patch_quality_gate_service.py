from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.patching.diff_proposal import DiffProposal
from aipinho.schemas.patching.patch_plan import PatchPlan
from aipinho.schemas.patching.quality.patch_quality_finding import PatchQualityFinding
from aipinho.schemas.patching.quality.patch_quality_gate_request import PatchQualityGateRequest
from aipinho.schemas.patching.quality.patch_quality_gate_result import PatchQualityGateResult
from aipinho.services.patching.patch_plan_store import PatchPlanStore
from aipinho.services.patching.quality.diff_header_validator import DiffHeaderValidator
from aipinho.services.patching.quality.diff_scope_validator import DiffScopeValidator
from aipinho.services.patching.quality.diff_stats_validator import DiffStatsValidator
from aipinho.services.patching.quality.evidence_link_validator import EvidenceLinkValidator
from aipinho.services.patching.quality.hardcode_detector import HardcodeDetector
from aipinho.services.patching.quality.hunk_consistency_validator import HunkConsistencyValidator
from aipinho.services.patching.quality.import_impact_analyzer import ImportImpactAnalyzer
from aipinho.services.patching.quality.patch_quality_audit_service import PatchQualityAuditService
from aipinho.services.patching.quality.patch_quality_decision_service import PatchQualityDecisionService
from aipinho.services.patching.quality.patch_quality_score_service import PatchQualityScoreService
from aipinho.services.patching.quality.patch_quality_store import PatchQualityStore
from aipinho.services.patching.quality.patch_quality_trace_service import PatchQualityTraceService
from aipinho.services.patching.quality.policy_bypass_detector import PolicyBypassDetector
from aipinho.services.patching.quality.rollback_note_validator import RollbackNoteValidator
from aipinho.services.patching.quality.schema_api_impact_analyzer import SchemaApiImpactAnalyzer
from aipinho.services.patching.quality.security_regression_detector import SecurityRegressionDetector
from aipinho.services.patching.quality.static_syntax_validator import StaticSyntaxValidator
from aipinho.services.patching.quality.target_snapshot_validator import TargetSnapshotValidator
from aipinho.services.patching.quality.test_plan_validator import TestPlanValidator
from aipinho.services.patching.quality.unified_diff_parser import UnifiedDiffParser
from aipinho.services.session.session_store import utc_now
from aipinho.utils.yaml_loader import inspect_yaml_file, load_yaml_file


class PatchQualityGateService:
    CONFIGS = [
        "patch_quality_gate_policy.yaml",
        "static_validation_policy.yaml",
        "diff_parse_policy.yaml",
        "hunk_validation_policy.yaml",
        "target_snapshot_validation_policy.yaml",
        "syntax_validation_policy.yaml",
        "hardcode_detection_policy.yaml",
        "policy_bypass_detection_policy.yaml",
        "security_regression_policy.yaml",
        "import_impact_policy.yaml",
        "schema_api_impact_policy.yaml",
        "test_plan_validation_policy.yaml",
        "rollback_validation_policy.yaml",
        "patch_quality_score_policy.yaml",
        "patch_quality_store_policy.yaml",
        "patch_quality_audit_policy.yaml",
    ]

    def __init__(self, plan_store: PatchPlanStore | None = None, quality_store: PatchQualityStore | None = None) -> None:
        self.plan_store = plan_store or PatchPlanStore()
        self.quality_store = quality_store or PatchQualityStore()
        self.policy = load_yaml_file(PATHS.config_root / "patching" / "quality" / "patch_quality_gate_policy.yaml", critical=True, root=PATHS.config_root / "patching" / "quality")
        self.trace_service = PatchQualityTraceService()
        self.parser = UnifiedDiffParser()
        self.header_validator = DiffHeaderValidator()
        self.scope_validator = DiffScopeValidator()
        self.stats_validator = DiffStatsValidator()
        self.hunk_validator = HunkConsistencyValidator()
        self.snapshot_validator = TargetSnapshotValidator()
        self.static_validator = StaticSyntaxValidator()
        self.hardcode_detector = HardcodeDetector()
        self.policy_bypass_detector = PolicyBypassDetector()
        self.security_detector = SecurityRegressionDetector()
        self.import_analyzer = ImportImpactAnalyzer()
        self.schema_api_analyzer = SchemaApiImpactAnalyzer()
        self.test_plan_validator = TestPlanValidator()
        self.rollback_validator = RollbackNoteValidator()
        self.evidence_validator = EvidenceLinkValidator()
        self.score_service = PatchQualityScoreService()
        self.decision_service = PatchQualityDecisionService()
        self.audit_service = PatchQualityAuditService()

    def validate_plan(self, plan_id: str) -> PatchQualityGateResult | None:
        plan = self.plan_store.get_plan(plan_id)
        if plan is None:
            return None
        result = self._validate(plan=plan, diff=plan.diff_proposal, request=None, refresh=False)
        plan.quality_gate = self._quality_summary(result)
        plan.apply_enabled = bool(result.apply_enabled and result.status == "passed")
        plan.write_enabled = bool(result.write_enabled and result.status == "passed")
        plan.safe_to_apply = bool(result.safe_for_future_apply_review and result.status == "passed")
        plan.updated_at = utc_now()
        self.plan_store.save_plan(plan)
        return result

    def refresh_plan(self, plan_id: str) -> PatchQualityGateResult | None:
        return self.validate_plan(plan_id)

    def validate_diff(self, request: PatchQualityGateRequest) -> PatchQualityGateResult:
        return self._validate(plan=None, diff=None, request=request, refresh=False)

    def validate_static(self, request: PatchQualityGateRequest) -> PatchQualityGateResult:
        return self._validate(plan=None, diff=None, request=request, refresh=False, static_only=True)

    def get_result(self, quality_id: str) -> PatchQualityGateResult | None:
        return self.quality_store.get_result(quality_id)

    def get_trace(self, quality_id: str) -> dict[str, object] | None:
        return self.quality_store.get_trace(quality_id)

    def get_latest_for_plan(self, plan_id: str) -> PatchQualityGateResult | None:
        return self.quality_store.get_latest_for_plan(plan_id)

    def list_results(self, *, plan_id: str | None = None, status: str | None = None, limit: int = 100) -> list[PatchQualityGateResult]:
        return self.quality_store.list_results(plan_id=plan_id, status=status, limit=limit)

    def _validate(
        self,
        *,
        plan: PatchPlan | None,
        diff: DiffProposal | None,
        request: PatchQualityGateRequest | None,
        refresh: bool,
        static_only: bool = False,
    ) -> PatchQualityGateResult:
        quality_id = f"patch_quality_{uuid4().hex}"
        trace = self.trace_service.create(quality_id)
        diff_text = self._diff_text(plan, diff, request)
        file_contents = self._file_contents(plan, request)
        proposed_contents = self._proposed_contents(plan, file_contents)
        if request and request.file_contents:
            proposed_contents = {**proposed_contents, **request.file_contents}
        parse = self.parser.parse(diff_text) if diff_text and not static_only else self.parser.parse(diff_text) if diff_text else self.parser.parse("".join(f"--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n" for path in proposed_contents))
        self.trace_service.add(trace, "diff_parsed")
        header_findings = self.header_validator.validate(parse)
        stats_findings = self.stats_validator.validate(parse)
        declared = [file.relative_path or file.path for file in plan.affected_files] if plan else (request.target_files if request else [])
        scope_findings = self.scope_validator.validate(parse, declared)
        hunk_validation = self.hunk_validator.validate(parse, file_contents) if file_contents and not static_only else self.hunk_validator.validate(parse, {})
        snapshot_validation = self.snapshot_validator.validate(plan.affected_files) if plan else self.snapshot_validator.validate([])
        static_validation = self.static_validator.validate(proposed_contents)
        hardcode_detection = self.hardcode_detector.detect(diff_text)
        policy_bypass_detection = self.policy_bypass_detector.detect(diff_text)
        security_regression = self.security_detector.detect(diff_text)
        import_impact = self.import_analyzer.analyze(diff_text)
        schema_api_impact = self.schema_api_analyzer.analyze(parse)
        test_plan_validation = self.test_plan_validator.validate(plan, diff, schema_api_impact)
        rollback_validation = self.rollback_validator.validate(plan)
        evidence_findings = self.evidence_validator.validate(plan)
        findings = [
            *parse.findings,
            *header_findings,
            *stats_findings,
            *scope_findings,
            *hunk_validation.findings,
            *snapshot_validation.findings,
            *static_validation.findings,
            *hardcode_detection.findings,
            *policy_bypass_detection.findings,
            *security_regression.findings,
            *import_impact.findings,
            *schema_api_impact.findings,
            *test_plan_validation.findings,
            *rollback_validation.findings,
            *evidence_findings,
        ]
        score = self.score_service.score(findings)
        status, safe_for_future_apply_review = self.decision_service.decide(score)
        policy = self.policy.get("patch_quality_gate", {}) if isinstance(self.policy.get("patch_quality_gate"), dict) else {}
        apply_enabled = bool(policy.get("apply_enabled", False)) and status == "passed" and safe_for_future_apply_review
        write_enabled = bool(policy.get("write_enabled", False)) and status == "passed" and safe_for_future_apply_review
        now = utc_now()
        self.trace_service.finish(trace, status)
        result = PatchQualityGateResult(
            quality_id=quality_id,
            plan_id=plan.plan_id if plan else request.plan_id if request else None,
            status=status,
            score=score,
            safe_for_future_apply_review=safe_for_future_apply_review,
            apply_enabled=apply_enabled,
            write_enabled=write_enabled,
            shell_enabled=False,
            git_enabled=False,
            test_execution_enabled=False,
            diff_parse=parse,
            hunk_validation=hunk_validation,
            target_snapshot_validation=snapshot_validation,
            static_validation=static_validation,
            hardcode_detection=hardcode_detection,
            policy_bypass_detection=policy_bypass_detection,
            security_regression=security_regression,
            import_impact=import_impact,
            schema_api_impact=schema_api_impact,
            test_plan_validation=test_plan_validation,
            rollback_validation=rollback_validation,
            findings=findings,
            warnings=list(dict.fromkeys([*parse.warnings, *hunk_validation.warnings, *snapshot_validation.warnings, *static_validation.warnings])),
            trace=trace,
            created_at=now,
            updated_at=now,
        )
        self.quality_store.save_result(result)
        self.audit_service.audit(result)
        return result

    def _diff_text(self, plan: PatchPlan | None, diff: DiffProposal | None, request: PatchQualityGateRequest | None) -> str:
        if request and request.diff_text:
            return request.diff_text
        if diff is not None:
            return diff.diff.diff_text
        if plan and plan.diff_proposal is not None:
            return plan.diff_proposal.diff.diff_text
        return ""

    def _file_contents(self, plan: PatchPlan | None, request: PatchQualityGateRequest | None) -> dict[str, str]:
        contents: dict[str, str] = {}
        if request and request.file_contents:
            contents.update(request.file_contents)
        if plan is None:
            return contents
        for affected in plan.affected_files:
            if not affected.normalized_path:
                continue
            path = Path(affected.normalized_path)
            if not path.exists() or not path.is_file():
                continue
            try:
                contents[affected.relative_path or affected.path] = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
        return contents

    def _proposed_contents(self, plan: PatchPlan | None, file_contents: dict[str, str]) -> dict[str, str]:
        if plan is None:
            return {}
        proposed = dict(file_contents)
        for hunk in plan.hunks:
            file_path = hunk.file_path
            content = self._lookup_content(file_path, proposed)
            if content is None:
                content = ""
            proposed[file_path] = content.replace(hunk.original, hunk.replacement, 1)
        return proposed

    def _lookup_content(self, file_path: str, contents: dict[str, str]) -> str | None:
        normalized = file_path.replace("\\", "/")
        for key, value in contents.items():
            key_normalized = key.replace("\\", "/")
            if key_normalized == normalized or key_normalized.endswith("/" + normalized):
                return value
        return None

    def _quality_summary(self, result: PatchQualityGateResult) -> dict[str, object]:
        return {
            "quality_id": result.quality_id,
            "status": result.status,
            "score": result.score.score,
            "safe_for_future_apply_review": result.safe_for_future_apply_review,
            "apply_enabled": result.apply_enabled,
            "write_enabled": result.write_enabled,
            "findings": len(result.findings),
            "blocking_findings": result.score.blocking_findings,
            "updated_at": result.updated_at,
        }

    def status(self) -> dict[str, object]:
        root = PATHS.config_root / "patching" / "quality"
        statuses = [inspect_yaml_file(root / name, root=root) for name in self.CONFIGS]
        warnings = [f"{item.path}:{item.status}" for item in statuses if item.status != "ok"]
        return {
            "status": "degraded" if warnings else "ok",
            "service": "patch_quality_gate",
            "mode": str((self.policy.get("patch_quality_gate", {}) or {}).get("mode", "static_validation_only")),
            "apply_enabled": bool((self.policy.get("patch_quality_gate", {}) or {}).get("apply_enabled", False)),
            "write_enabled": bool((self.policy.get("patch_quality_gate", {}) or {}).get("write_enabled", False)),
            "shell_enabled": False,
            "git_enabled": False,
            "test_execution_enabled": False,
            "warnings": warnings,
        }
