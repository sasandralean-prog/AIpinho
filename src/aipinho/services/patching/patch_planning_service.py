from __future__ import annotations

from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.patching.affected_file import AffectedFile
from aipinho.schemas.patching.canonical_diagnosis_artifact import CanonicalDiagnosisArtifact
from aipinho.schemas.patching.diff_proposal import DiffProposal
from aipinho.schemas.patching.patch_candidate_artifact import PatchCandidateArtifact
from aipinho.schemas.patching.patch_evidence import PatchEvidence
from aipinho.schemas.patching.patch_hunk import PatchHunk
from aipinho.schemas.patching.patch_plan import PatchPlan
from aipinho.schemas.patching.patch_plan_request import PatchPlanRequest
from aipinho.schemas.patching.patch_plan_result import PatchPlanResult
from aipinho.schemas.patching.patch_status import PatchPlanningStatus
from aipinho.services.patching.affected_file_resolver import AffectedFileResolver
from aipinho.services.patching.diff_proposal_service import DiffProposalService
from aipinho.services.patching.diagnosis_runtime_service import DiagnosisRuntimeService
from aipinho.services.patching.patch_evidence_service import PatchEvidenceService
from aipinho.services.patching.patch_file_reader import PatchFileReader
from aipinho.services.patching.patch_hunk_builder import PatchHunkBuilder
from aipinho.services.patching.patch_plan_store import PatchPlanStore
from aipinho.services.patching.patch_risk_service import PatchRiskService
from aipinho.services.patching.patch_scope_service import PatchScopeService
from aipinho.services.patching.patch_source_resolver import PatchSourceResolver
from aipinho.services.patching.patch_target_guard import PatchTargetGuard
from aipinho.services.patching.patch_test_recommendation_service import PatchTestRecommendationService
from aipinho.services.patching.patch_validation_service import PatchValidationService
from aipinho.services.patching.rollback_note_service import RollbackNoteService
from aipinho.services.session.session_store import utc_now
from aipinho.utils.yaml_loader import inspect_yaml_file, load_yaml_file


class PatchPlanningService:
    CONFIGS = [
        "patch_planning_policy.yaml",
        "patch_scope_policy.yaml",
        "patch_target_policy.yaml",
        "diff_proposal_policy.yaml",
        "patch_evidence_policy.yaml",
        "patch_risk_policy.yaml",
        "patch_validation_policy.yaml",
        "rollback_note_policy.yaml",
        "patch_test_recommendation_policy.yaml",
        "patch_store_policy.yaml",
        "patch_audit_policy.yaml",
    ]

    def __init__(self, store: PatchPlanStore | None = None) -> None:
        self.store = store or PatchPlanStore()
        self.source_resolver = PatchSourceResolver()
        self.diagnosis_runtime = DiagnosisRuntimeService()
        self.affected_resolver = AffectedFileResolver()
        self.scope_service = PatchScopeService()
        self.target_guard = PatchTargetGuard()
        self.file_reader = PatchFileReader()
        self.evidence_service = PatchEvidenceService()
        self.hunk_builder = PatchHunkBuilder()
        self.diff_service = DiffProposalService()
        self.risk_service = PatchRiskService()
        self.rollback_service = RollbackNoteService()
        self.tests_service = PatchTestRecommendationService()
        self.validation_service = PatchValidationService()
        self.policy = load_yaml_file(PATHS.config_root / "patching" / "patch_planning_policy.yaml", critical=True, root=PATHS.config_root / "patching")
        self.scope_policy = load_yaml_file(PATHS.config_root / "patching" / "patch_scope_policy.yaml", critical=True, root=PATHS.config_root / "patching")
        self.target_policy = load_yaml_file(PATHS.config_root / "patching" / "patch_target_policy.yaml", critical=True, root=PATHS.config_root / "patching")

    def create_plan(self, request: PatchPlanRequest) -> PatchPlanResult:
        plan_id = f"patch_plan_{uuid4().hex}"
        trace = ["patch_planning_started"]
        evidence, source_warnings, source_blocked = self.source_resolver.resolve(request)
        initial_paths = self.affected_resolver.resolve(request.affected_files, evidence)
        diagnoses = self._build_diagnoses(request, initial_paths, evidence)
        candidates = self._build_patch_candidates(diagnoses)
        paths = self.affected_resolver.resolve(
            [*initial_paths, *[candidate.target_file for candidate in candidates]],
            evidence,
        )
        evidence = self.evidence_service.normalize(evidence, user_request=request.objective, affected_paths=paths)
        diagnoses = self._build_diagnoses(request, paths, evidence)
        candidates = self._build_patch_candidates(diagnoses)
        evidence_valid, evidence_blocked = self.evidence_service.validate(evidence)
        scope = self.scope_service.build(request.workspace, paths)
        affected = [self.target_guard.validate(request.workspace, path) for path in scope.affected_paths]
        file_contents: dict[str, str] = {}
        for index, file in enumerate(list(affected)):
            checked, content = self.file_reader.read(file)
            affected[index] = checked
            if checked.status != "blocked" and checked.normalized_path:
                file_contents[checked.normalized_path] = content
        hunks: list[PatchHunk] = []
        diff: DiffProposal | None = None
        compiler_blocked: list[str] = []
        compiler_warnings: list[str] = []
        if evidence_valid and affected and not any(file.status == "blocked" for file in affected):
            hunks, diff, compiler_blocked, compiler_warnings = self._compile_patch_candidates(
                plan_id=plan_id,
                candidates=candidates,
                affected=affected,
                file_contents=file_contents,
                replacements=request.replacements,
            )
        risk = self.risk_service.assess(affected, evidence_count=len(evidence), diff_chars=diff.diff.chars if diff else 0)
        rollback_notes = self.rollback_service.build(affected)
        test_recommendations = self.tests_service.recommend(affected)
        validation = self.validation_service.validate(evidence=evidence, diff=diff, risk=risk, rollback_notes=rollback_notes, test_recommendations=test_recommendations)
        replacement_blocked = ["INSUFFICIENT_PATCH_EVIDENCE"] if affected and candidates and not any(request.replacements.values()) else []
        blocked = list(dict.fromkeys([*source_blocked, *evidence_blocked, *replacement_blocked, *compiler_blocked, *scope.omitted_paths, *[reason for file in affected for reason in file.blocked_reasons], *validation.blocked_reasons]))
        status = "blocked" if blocked or risk.blocked else validation.status
        if status == "ready_for_review" and risk.needs_review:
            status = "needs_review"
        now = utc_now()
        trace.append(f"patch_planning_finished:{status}")
        plan = PatchPlan(
            plan_id=plan_id,
            status=status,
            workspace=request.workspace,
            source_type=request.source_type,
            source_id=request.source_id,
            objective=request.objective,
            affected_files=affected,
            diagnosis_artifacts=diagnoses,
            patch_candidates=candidates,
            evidence=evidence,
            hunks=hunks,
            diff_proposal=diff,
            risk=risk,
            validation=validation,
            rollback_notes=rollback_notes,
            test_recommendations=test_recommendations,
            quality_gate=self._quality_gate(diagnoses, candidates),
            apply_enabled=False,
            write_enabled=False,
            safe_to_apply=False,
            created_at=now,
            updated_at=now,
            warnings=list(dict.fromkeys([*source_warnings, *compiler_warnings, *scope.omitted_paths])),
            blocked_reasons=blocked,
            trace=trace,
        )
        self.store.save_plan(plan)
        return PatchPlanResult(status=plan.status, plan=plan, apply_enabled=plan.apply_enabled, write_enabled=plan.write_enabled)

    def refresh(self, plan_id: str) -> PatchPlan | None:
        plan = self.store.get_plan(plan_id)
        if plan is None:
            return None
        request = PatchPlanRequest(workspace=plan.workspace, source_type=plan.source_type, source_id=plan.source_id, objective=plan.objective, affected_files=[file.path for file in plan.affected_files], diagnosis_artifacts=plan.diagnosis_artifacts, patch_candidates=plan.patch_candidates, evidence=plan.evidence)
        refreshed = self.create_plan(request).plan
        refreshed.plan_id = plan.plan_id
        self.store.save_plan(refreshed)
        return refreshed

    def validate_plan(self, plan_id: str):
        plan = self.store.get_plan(plan_id)
        if plan is None:
            return None
        plan.validation = self.validation_service.validate(evidence=plan.evidence, diff=plan.diff_proposal, risk=plan.risk, rollback_notes=plan.rollback_notes, test_recommendations=plan.test_recommendations)
        plan.updated_at = utc_now()
        self.store.save_plan(plan)
        return plan.validation

    def get_plan(self, plan_id: str):
        return self.store.get_plan(plan_id)

    def get_diff(self, plan_id: str):
        return self.store.get_diff(plan_id)

    def get_evidence(self, plan_id: str):
        return self.store.get_evidence(plan_id)

    def get_risk(self, plan_id: str):
        return self.store.get_risk(plan_id)

    def get_trace(self, plan_id: str):
        return self.store.get_trace(plan_id)

    def list_plans(self, **filters):
        return self.store.list_plans(**filters)

    def status(self) -> PatchPlanningStatus:
        statuses = [inspect_yaml_file(PATHS.config_root / "patching" / name, root=PATHS.config_root / "patching") for name in self.CONFIGS]
        warnings = [f"{status.path}:{status.status}" for status in statuses if status.status != "ok"]
        patching = self.policy.get("patch_planning", {}) if isinstance(self.policy.get("patch_planning"), dict) else {}
        targets = self.target_policy.get("targets", {}) if isinstance(self.target_policy.get("targets"), dict) else {}
        scope = self.scope_policy.get("scope", {}) if isinstance(self.scope_policy.get("scope"), dict) else {}
        return PatchPlanningStatus(status="degraded" if warnings else "ok", enabled=bool(patching.get("enabled", True)), mode=str(patching.get("mode", "proposal_only")), apply_enabled=bool(patching.get("apply_enabled", False)), write_enabled=bool(patching.get("write_enabled", False)), shell_enabled=False, git_write_enabled=False, test_execution_enabled=False, real_model_auto_use=bool(patching.get("model_assisted_default", False)), allowed_extensions=list(targets.get("allowed_extensions", []) or []), blocked_extensions=list(targets.get("blocked_extensions", []) or []), max_files_per_plan=int(scope.get("max_files_per_plan", 5)), max_total_hunks=int(scope.get("max_total_hunks", 20)), warnings=warnings)

    def _default_replacement(self, content: str) -> str:
        return ""

    def _build_diagnoses(
        self,
        request: PatchPlanRequest,
        paths: list[str],
        evidence: list[PatchEvidence],
    ) -> list[CanonicalDiagnosisArtifact]:
        if request.diagnosis_artifacts:
            return list(request.diagnosis_artifacts)
        return self.diagnosis_runtime.diagnoses_from_request(
            workspace=request.workspace,
            objective=request.objective,
            source_type=request.source_type,
            source_id=request.source_id,
            paths=paths,
            evidence=evidence,
            candidates=request.patch_candidates,
        )

    def _build_patch_candidates(
        self,
        diagnoses: list[CanonicalDiagnosisArtifact],
    ) -> list[PatchCandidateArtifact]:
        return self.diagnosis_runtime.candidates_from_diagnoses(diagnoses)

    def _quality_gate(
        self,
        diagnoses: list[CanonicalDiagnosisArtifact],
        candidates: list[PatchCandidateArtifact],
    ) -> dict[str, object]:
        diagnosis_quality = [
            candidate.technical_context.get("diagnosis_quality")
            for candidate in candidates
            if isinstance(candidate.technical_context.get("diagnosis_quality"), dict)
        ]
        candidate_quality = [
            candidate.technical_context.get("patch_candidate_quality")
            for candidate in candidates
            if isinstance(candidate.technical_context.get("patch_candidate_quality"), dict)
        ]
        actionability = [
            candidate.technical_context.get("actionability")
            for candidate in candidates
            if isinstance(candidate.technical_context.get("actionability"), dict)
        ]
        reason_codes: list[str] = []
        for item in [*diagnosis_quality, *candidate_quality, *actionability]:
            if isinstance(item, dict):
                reason_codes.extend(str(reason) for reason in item.get("reason_codes", []) if reason)
        return {
            "diagnosis_count": len(diagnoses),
            "patch_candidate_count": len(candidates),
            "diagnosis_quality": diagnosis_quality,
            "patch_candidate_quality": candidate_quality,
            "actionability": actionability,
            "reason_codes": list(dict.fromkeys(reason_codes)),
        }

    def _compile_patch_candidates(
        self,
        *,
        plan_id: str,
        candidates: list[PatchCandidateArtifact],
        affected: list[AffectedFile],
        file_contents: dict[str, str],
        replacements: dict[str, str],
    ) -> tuple[list[PatchHunk], DiffProposal | None, list[str], list[str]]:
        if not candidates:
            return [], None, ["PATCH_CANDIDATE_INSUFFICIENT"], []
        affected_by_path: dict[str, AffectedFile] = {}
        for file in affected:
            for key in (file.relative_path, file.path):
                if key:
                    affected_by_path[key.replace("\\", "/")] = file
        blocked: list[str] = []
        warnings: list[str] = []
        for candidate in candidates:
            candidate_key = candidate.target_file.replace("\\", "/")
            affected_file = affected_by_path.get(candidate_key)
            if affected_file is None:
                warnings.append("PATCH_CANDIDATE_TARGET_NOT_IN_SCOPE")
                continue
            replacement = self._replacement_for_candidate(candidate, affected_file, replacements)
            if not self._candidate_has_required_evidence(candidate):
                blocked.append("PATCH_CANDIDATE_INSUFFICIENT")
                continue
            if replacement is None or not replacement.strip():
                blocked.append("INSUFFICIENT_PATCH_EVIDENCE")
                continue
            content = file_contents.get(affected_file.normalized_path or "", "")
            original, context_error = self._extract_candidate_context(candidate, content)
            if context_error:
                blocked.append(context_error)
                continue
            if not original.strip():
                blocked.append("PATCH_CONTEXT_TOO_SMALL")
                continue
            if replacement == original:
                blocked.append("PATCH_REPLACEMENT_INVALID")
                continue
            file_path = affected_file.relative_path or affected_file.path
            hunk = PatchHunk(
                hunk_id=f"patch_hunk_{uuid4().hex}",
                file_path=file_path,
                original=original,
                replacement=replacement,
                reason="Compiled from governed PatchCandidateArtifact.",
                evidence_ids=list(candidate.evidence_refs),
                confidence=candidate.confidence,
            )
            diff = self.diff_service.create(plan_id, file_path, content, [hunk])
            if diff.status != "generated":
                return [], diff, list(dict.fromkeys([*blocked, *diff.blocked_reasons, "PATCH_COMPILER_FAILED"])), warnings
            return [hunk], diff, list(dict.fromkeys(blocked)), warnings
        return [], None, list(dict.fromkeys(blocked or ["PATCH_COMPILER_FAILED"])), warnings

    def _replacement_for_candidate(
        self,
        candidate: PatchCandidateArtifact,
        affected_file: AffectedFile,
        replacements: dict[str, str],
    ) -> str | None:
        keys = [
            candidate.target_file,
            candidate.target_file.replace("\\", "/"),
            affected_file.relative_path or "",
            affected_file.path,
            affected_file.normalized_path or "",
        ]
        for key in keys:
            if key and key in replacements:
                return replacements[key]
        return None

    def _candidate_has_required_evidence(self, candidate: PatchCandidateArtifact) -> bool:
        return bool(
            candidate.target_file
            and candidate.diagnosis_id
            and candidate.target_symbol
            and candidate.observed_behavior
            and candidate.expected_behavior
            and candidate.evidence_refs
        )

    def _extract_candidate_context(self, candidate: PatchCandidateArtifact, content: str) -> tuple[str, str | None]:
        if candidate.symbol_kind == "file":
            return content, None
        symbol = candidate.target_symbol.strip()
        if not symbol:
            return "", "PATCH_CANDIDATE_INSUFFICIENT"
        lines = content.splitlines(keepends=True)
        start = None
        for index, line in enumerate(lines):
            stripped = line.strip()
            if (
                stripped.startswith(f"def {symbol}(")
                or stripped.startswith(f"async def {symbol}(")
                or stripped.startswith(f"class {symbol}(")
                or stripped.startswith(f"class {symbol}:")
                or stripped.startswith(f"fun {symbol}(")
                or stripped.startswith(f"function {symbol}(")
            ):
                start = index
                break
        if start is None:
            return "", "PATCH_SYMBOL_NOT_FOUND"
        base_indent = len(lines[start]) - len(lines[start].lstrip())
        end = len(lines)
        for index in range(start + 1, len(lines)):
            stripped = lines[index].strip()
            if not stripped:
                continue
            indent = len(lines[index]) - len(lines[index].lstrip())
            if indent <= base_indent:
                end = index
                break
        return "".join(lines[start:end]), None
