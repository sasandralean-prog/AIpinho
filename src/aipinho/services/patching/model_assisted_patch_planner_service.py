from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.analysis.file_context_bundle import FileContextBundle
from aipinho.schemas.analysis.file_selection import FileSelectionRequest
from aipinho.schemas.analysis.project_analysis_request import ProjectAnalysisRequest
from aipinho.schemas.patching.canonical_diagnosis_artifact import CanonicalDiagnosisArtifact, DiagnosisEvidenceRef, DiagnosisMetadata, RepairHint, TechnicalLocalization
from aipinho.schemas.patching.model_patch_proposal import ModelPatchPlanningResult, ModelPatchProposal, ModelReplacementProposal
from aipinho.schemas.patching.patch_candidate_artifact import PatchCandidateArtifact
from aipinho.schemas.patching.patch_evidence import PatchEvidence
from aipinho.schemas.patching.patch_plan_request import PatchPlanRequest
from aipinho.schemas.patching.repair_proposal_artifact import (
    RepairProposalAssembly,
    RepairProposalAssemblyStage,
    RepairProposalArtifact,
    RepairProposalConcreteChange,
    RepairProposalImpact,
    RepairProposalRisks,
    RepairProposalRollback,
    RepairProposalTarget,
)
from aipinho.schemas.roles.role_model_binding import RoleInferenceRequest
from aipinho.services.analysis.project_analysis_service import ProjectAnalysisService
from aipinho.services.patching.diagnosis_runtime_service import DiagnosisRuntimeService
from aipinho.services.patching.patch_planning_service import PatchPlanningService
from aipinho.services.patching.semantic_proposal_compiler import SemanticProposalCompiler
from aipinho.services.roles.role_inference_budget_service import RoleInferenceBudgetService
from aipinho.services.roles.role_inference_service import RoleInferenceService
from aipinho.utils.yaml_loader import load_yaml_file


class ModelAssistedPatchPlannerService:
    """Builds a patch preview from bounded, read-only file context.

    The model can propose replacement text, but PatchPlanningService remains the
    only component that validates paths and creates the governed diff artifact.
    """

    def __init__(
        self,
        *,
        roles: RoleInferenceService | None = None,
        planning: PatchPlanningService | None = None,
        analysis: ProjectAnalysisService | None = None,
        budget: RoleInferenceBudgetService | None = None,
        proposal_compiler: SemanticProposalCompiler | None = None,
        policy: dict[str, Any] | None = None,
    ) -> None:
        self.roles = roles or RoleInferenceService()
        self.planning = planning or PatchPlanningService()
        self.diagnosis_runtime = DiagnosisRuntimeService()
        self.analysis = analysis or ProjectAnalysisService()
        self.budget = budget or RoleInferenceBudgetService()
        self.proposal_compiler = proposal_compiler or SemanticProposalCompiler()
        self.policy = policy or load_yaml_file(
            PATHS.config_root / "patching" / "model_patch_planner_policy.yaml",
            critical=True,
            root=PATHS.config_root / "patching",
        )

    def create_plan(
        self,
        *,
        workspace: str,
        objective: str,
        source_id: str | None = None,
        file_context_bundle: FileContextBundle | dict[str, Any] | None = None,
        evidence_context: list[dict[str, Any]] | None = None,
        include_trace: bool = False,
    ) -> ModelPatchPlanningResult:
        settings = self._settings()
        if not bool(settings.get("enabled", False)):
            return ModelPatchPlanningResult(status="blocked", blocked_reasons=["model_patch_planner_disabled"])
        role_id = str(settings.get("role_id", "patch_planner"))
        prompt = self._proposal_prompt()
        context_limit = self._role_context_limit(role_id, prompt, settings)
        ranked_evidence = self._rank_evidence_context(objective, evidence_context or [])
        bundle = self._coerce_or_build_context(workspace, file_context_bundle, settings, objective=objective, evidence_context=ranked_evidence)
        candidates, budget_warnings = self._candidate_files(
            workspace,
            bundle,
            settings,
            objective=objective,
            evidence_context=ranked_evidence,
            context_limit=context_limit,
        )
        if not candidates:
            return ModelPatchPlanningResult(
                status="blocked",
                blocked_reasons=["model_patch_context_unavailable"],
                warnings=list(getattr(bundle, "warnings", []) or []),
            )
        diagnosis = self._diagnosis_artifact(
            workspace=workspace,
            objective=objective,
            source_id=source_id or bundle.bundle_id,
            candidates=candidates,
            evidence_context=ranked_evidence,
        )
        if diagnosis is None:
            return ModelPatchPlanningResult(
                status="blocked",
                blocked_reasons=["PATCH_CANDIDATE_INSUFFICIENT"],
                warnings=list(dict.fromkeys([*budget_warnings, *list(getattr(bundle, "warnings", []) or [])])),
            )
        diagnosis = self.diagnosis_runtime.enrich_diagnosis(diagnosis)
        patch_candidates = self.diagnosis_runtime.candidates_from_diagnosis(
            diagnosis,
            current_content_by_path={item["path"]: item["content"] for item in candidates},
        )
        patch_candidate = patch_candidates[0] if patch_candidates else None
        if patch_candidate is None:
            return ModelPatchPlanningResult(
                status="blocked",
                blocked_reasons=["PATCH_CANDIDATE_INSUFFICIENT"],
                warnings=list(dict.fromkeys([*budget_warnings, *list(getattr(bundle, "warnings", []) or [])])),
            )
        context = self._role_context(
            objective,
            candidates,
            settings,
            evidence_context=ranked_evidence,
            patch_candidate=patch_candidate,
        )
        context = self._fit_role_context_to_budget(context, context_limit)
        self._mark_candidate_context_completeness(patch_candidate, candidates, context)
        actionability = self.diagnosis_runtime.enrich_actionability(
            patch_candidate,
            policy=self._actionability_policy(settings),
        )
        proposal_scaffold = self.proposal_compiler.compile(patch_candidate)
        patch_candidate.technical_context = {
            **dict(patch_candidate.technical_context),
            "repair_proposal_scaffold": proposal_scaffold.model_dump(mode="json"),
        }
        if not actionability.editable:
            return ModelPatchPlanningResult(
                status="blocked",
                repair_proposal=proposal_scaffold,
                warnings=list(dict.fromkeys([*budget_warnings, *list(getattr(bundle, "warnings", []) or [])])),
                blocked_reasons=list(dict.fromkeys(["REPAIR_TASK_NOT_ACTIONABLE", *actionability.reason_codes])),
                metadata={
                    **self._candidate_metadata(patch_candidate),
                    "repair_proposal": proposal_scaffold.model_dump(mode="json"),
                },
            )
        alignment = self.diagnosis_runtime.alignment_for_candidate(patch_candidate)
        if not alignment.aligned:
            return ModelPatchPlanningResult(
                status="blocked",
                repair_proposal=proposal_scaffold,
                warnings=list(dict.fromkeys([*budget_warnings, *list(getattr(bundle, "warnings", []) or [])])),
                blocked_reasons=list(dict.fromkeys(["REPAIR_TASK_ALIGNMENT_FAILED", *alignment.reason_codes])),
                metadata={
                    **self._candidate_metadata(patch_candidate),
                    "repair_proposal": proposal_scaffold.model_dump(mode="json"),
                },
            )
        if isinstance(context.get("patch_candidate"), dict):
            context["patch_candidate"] = self._role_patch_candidate(patch_candidate, settings)
            context = self._fit_role_context_to_budget(context, context_limit)
        role_request = RoleInferenceRequest(
            role_id=role_id,
            prompt=prompt,
            context=context,
            output_contract="patch_plan_draft_output",
            include_trace=include_trace,
            metadata={
                "planning_only": True,
                "model_patch_planner": True,
                "max_output_tokens": int(settings.get("max_output_tokens", 256) or 256),
                "timeout_seconds": int(settings.get("timeout_seconds", 90) or 90),
                "max_stdout_chars": int(settings.get("max_stdout_chars", 12000) or 12000),
                "max_stderr_chars": int(settings.get("max_stderr_chars", 8000) or 8000),
            },
        )
        model_run = self.roles.run(role_id, role_request)
        if not self._accepted_model_run(model_run, settings):
            return ModelPatchPlanningResult(
                status="blocked",
                repair_proposal=proposal_scaffold,
                model_run_id=model_run.run_id,
                model_id=model_run.selected_model_id,
                provider_id=model_run.provider_id,
                warnings=list(dict.fromkeys([*budget_warnings, *model_run.warnings])),
                blocked_reasons=list(dict.fromkeys([*model_run.blocked_reasons, "model_patch_proposal_unavailable"])),
                metadata={
                    "model_status": model_run.status,
                    "fallback_used": model_run.fallback_used,
                    **self._candidate_metadata(patch_candidate),
                    "repair_proposal": proposal_scaffold.model_dump(mode="json"),
                },
            )
        proposal, parse_error = self._parse_repair_proposal(model_run.output, patch_candidate)
        proposal_source_error = parse_error
        if proposal is None and parse_error:
            proposal = self.proposal_compiler.partial(
                patch_candidate,
                warning=parse_error,
            )
        if proposal is not None:
            proposal = self.proposal_compiler.merge(
                proposal,
                patch_candidate,
            )
        if proposal is None:
            return ModelPatchPlanningResult(
                status="blocked",
                repair_proposal=proposal_scaffold,
                model_run_id=model_run.run_id,
                model_id=model_run.selected_model_id,
                provider_id=model_run.provider_id,
                warnings=list(dict.fromkeys([*budget_warnings, *model_run.warnings])),
                blocked_reasons=[parse_error or "PATCH_REPLACEMENT_INVALID"],
                metadata={
                    **self._candidate_metadata(patch_candidate),
                    "repair_proposal": proposal_scaffold.model_dump(mode="json"),
                    "inference_input_doctor": model_run.metadata.get("inference_input_doctor", {}),
                    "canonical_inference_input_artifact": model_run.metadata.get("canonical_inference_input_artifact", {}),
                    "canonical_inference_output_artifact": model_run.metadata.get("canonical_inference_output_artifact", {}),
                },
            )
        proposal_errors = self._validate_repair_proposal(proposal, patch_candidate)
        if proposal_errors:
            return ModelPatchPlanningResult(
                status="blocked",
                repair_proposal=proposal,
                model_run_id=model_run.run_id,
                model_id=model_run.selected_model_id,
                provider_id=model_run.provider_id,
                warnings=list(dict.fromkeys([*budget_warnings, *model_run.warnings])),
                blocked_reasons=list(dict.fromkeys(([proposal_source_error] if proposal_source_error else []) + proposal_errors)),
                metadata={
                    **self._candidate_metadata(patch_candidate),
                    "repair_proposal": proposal.model_dump(mode="json"),
                    "inference_input_doctor": model_run.metadata.get("inference_input_doctor", {}),
                    "canonical_inference_input_artifact": model_run.metadata.get("canonical_inference_input_artifact", {}),
                    "canonical_inference_output_artifact": model_run.metadata.get("canonical_inference_output_artifact", {}),
                },
            )
        replacement = proposal.compiler_replacement()
        if not replacement:
            return ModelPatchPlanningResult(
                status="proposal_ready",
                repair_proposal=proposal,
                model_run_id=model_run.run_id,
                model_id=model_run.selected_model_id,
                provider_id=model_run.provider_id,
                warnings=list(dict.fromkeys([*budget_warnings, *model_run.warnings])),
                blocked_reasons=["PATCH_MODEL_EMPTY_OUTPUT"],
                metadata={
                    **self._candidate_metadata(patch_candidate),
                    "repair_proposal": proposal.model_dump(mode="json"),
                    "inference_input_doctor": model_run.metadata.get("inference_input_doctor", {}),
                    "canonical_inference_input_artifact": model_run.metadata.get("canonical_inference_input_artifact", {}),
                    "canonical_inference_output_artifact": model_run.metadata.get("canonical_inference_output_artifact", {}),
                },
            )
        validation_error = self._validate_replacement(replacement, patch_candidate, candidates)
        if validation_error:
            return ModelPatchPlanningResult(
                status="blocked",
                repair_proposal=proposal,
                model_run_id=model_run.run_id,
                model_id=model_run.selected_model_id,
                provider_id=model_run.provider_id,
                warnings=list(dict.fromkeys([*budget_warnings, *model_run.warnings])),
                blocked_reasons=[validation_error],
                metadata={
                    **self._candidate_metadata(patch_candidate),
                    "repair_proposal": proposal.model_dump(mode="json"),
                    "inference_input_doctor": model_run.metadata.get("inference_input_doctor", {}),
                    "canonical_inference_input_artifact": model_run.metadata.get("canonical_inference_input_artifact", {}),
                    "canonical_inference_output_artifact": model_run.metadata.get("canonical_inference_output_artifact", {}),
                },
            )
        evidence_excerpt = (
            proposal.concrete_change.reasoning
            or proposal.concrete_change.modification_strategy
            or patch_candidate.observed_behavior
        )
        evidence = PatchEvidence(
            evidence_id=f"model_patch_context:{source_id or bundle.bundle_id}",
            source_type=str(settings.get("source_type", "file_context_bundle")),
            source_id=source_id or bundle.bundle_id,
            source_path=patch_candidate.target_file,
            excerpt=evidence_excerpt,
            confidence=0.7,
        )
        plan_result = self.planning.create_plan(
            PatchPlanRequest(
                workspace=workspace,
                source_type=str(settings.get("source_type", "file_context_bundle")),
                source_id=source_id or bundle.bundle_id,
                objective=objective,
                affected_files=[patch_candidate.target_file],
                diagnosis_artifacts=[diagnosis],
                patch_candidates=[patch_candidate],
                evidence=[evidence],
                replacements={patch_candidate.target_file: replacement},
                model_assisted=True,
                include_trace=include_trace,
            )
        )
        accepted_statuses = {str(status) for status in settings.get("accepted_plan_statuses", [])}
        if plan_result.plan is not None:
            plan_result.plan.repair_proposal = proposal
            self.planning.store.save_plan(plan_result.plan)
        status = "ready" if plan_result.status in accepted_statuses else "blocked"
        return ModelPatchPlanningResult(
            status=status,
            plan=plan_result.plan,
            repair_proposal=proposal,
            model_run_id=model_run.run_id,
            model_id=model_run.selected_model_id,
            provider_id=model_run.provider_id,
            warnings=list(dict.fromkeys([*budget_warnings, *model_run.warnings, *plan_result.plan.warnings])),
            blocked_reasons=list(plan_result.plan.blocked_reasons),
            metadata={
                "model_assisted": True,
                "patch_candidate_id": patch_candidate.candidate_id,
                "proposal_path": patch_candidate.target_file,
                "plan_status": plan_result.status,
                "repair_proposal": proposal.model_dump(mode="json"),
                **self._candidate_metadata(patch_candidate),
                "inference_input_doctor": model_run.metadata.get("inference_input_doctor", {}),
                "canonical_inference_input_artifact": model_run.metadata.get("canonical_inference_input_artifact", {}),
                "canonical_inference_output_artifact": model_run.metadata.get("canonical_inference_output_artifact", {}),
            },
        )

    def status(self) -> dict[str, object]:
        settings = self._settings()
        return {
            "status": "ok" if settings.get("enabled", False) else "disabled",
            "service": "model_assisted_patch_planner",
            "role_id": settings.get("role_id"),
            "max_candidate_files": settings.get("max_candidate_files"),
            "max_replacements_per_plan": 1,
            "write_enabled": False,
            "apply_enabled": False,
        }

    def _actionability_policy(self, settings: dict[str, Any]) -> dict[str, Any]:
        configured = settings.get("actionability", {})
        policy = dict(configured) if isinstance(configured, dict) else {}
        policy.setdefault("max_file_edit_chars", settings.get("max_replacement_context_chars"))
        return policy

    def _candidate_metadata(self, patch_candidate: PatchCandidateArtifact) -> dict[str, Any]:
        technical_context = dict(patch_candidate.technical_context)
        return {
            "patch_candidate_id": patch_candidate.candidate_id,
            "diagnosis_id": patch_candidate.diagnosis_id,
            "repair_task": technical_context.get("repair_task", {}),
            "actionability": technical_context.get("actionability", {}),
            "repair_intent": technical_context.get("repair_intent", {}),
            "alignment": technical_context.get("alignment", {}),
            "diagnosis_quality": technical_context.get("diagnosis_quality", {}),
            "patch_candidate_quality": technical_context.get("patch_candidate_quality", {}),
            "semantic_evidence": technical_context.get("semantic_evidence", {}),
            "behavior_localization": technical_context.get("behavior_localization", {}),
            "behavior_justification": technical_context.get("behavior_justification", {}),
            "candidate_transformation": technical_context.get("candidate_transformation", {}),
            "repair_proposal_scaffold": technical_context.get("repair_proposal_scaffold", {}),
        }

    def _settings(self) -> dict[str, Any]:
        value = self.policy.get("model_patch_planner", {})
        return value if isinstance(value, dict) else {}

    def _coerce_or_build_context(
        self,
        workspace: str,
        bundle: FileContextBundle | dict[str, Any] | None,
        settings: dict[str, Any],
        *,
        objective: str = "",
        evidence_context: list[dict[str, Any]] | None = None,
    ) -> FileContextBundle:
        if isinstance(bundle, FileContextBundle):
            return bundle
        if isinstance(bundle, dict) and bundle:
            return FileContextBundle(**bundle)
        request = ProjectAnalysisRequest(
            workspace=workspace,
            prompt=objective,
            goal="patch_planning",
            focus_paths=self._focus_paths_from_evidence(workspace, evidence_context or [], settings),
            max_files=max(1, int(settings.get("max_candidate_files", 8))),
            max_total_bytes=max(1, int(settings.get("max_context_chars", 48000))),
            include_trace=False,
        )
        tree = self.analysis.tree_service.build_tree_summary(request)
        selection = self.analysis.selection_service.select_files(
            FileSelectionRequest(
                workspace=request.workspace,
                goal=request.goal,
                semantic_query=request.prompt,
                candidate_files=list(tree.candidate_files),
                focus_paths=request.focus_paths,
                max_files=request.max_files,
                max_total_bytes=request.max_total_bytes,
            ),
            project_tree=tree,
        )
        return self.analysis.context_builder.build_context(request, selection)

    def _candidate_files(
        self,
        workspace: str,
        bundle: FileContextBundle,
        settings: dict[str, Any],
        *,
        objective: str,
        evidence_context: list[dict[str, Any]],
        context_limit: int,
    ) -> tuple[list[dict[str, str]], list[str]]:
        root = Path(workspace).resolve()
        max_files = max(1, int(settings.get("max_candidate_files", 8)))
        per_file = max(1, int(settings.get("max_file_context_chars", 12000)))
        remaining = max(1, min(int(settings.get("max_context_chars", 48000)), context_limit))
        candidates: list[dict[str, Any]] = []
        warnings: list[str] = []
        eligible_items = [
            item
            for item in bundle.items
            if item.status == "included" and item.content and self._relative_candidate_path(root, item.path)
        ]
        guidance = self._guidance_text(objective, evidence_context)
        eligible_items = sorted(
            eligible_items,
            key=lambda item: self._candidate_priority(root, item.path, guidance),
            reverse=True,
        )
        for item in eligible_items:
            if item.status != "included" or not item.content:
                continue
            relative = self._relative_candidate_path(root, item.path)
            if not relative:
                continue
            content = item.content[: min(per_file, remaining)]
            if not content:
                continue
            content_complete = not bool(item.content_truncated) and len(content) >= len(item.content)
            next_candidates = [*candidates, {"path": relative, "content": content, "content_complete": content_complete}]
            next_context = self._role_context(objective, next_candidates, settings, evidence_context=evidence_context)
            next_size = len(str(next_context))
            if next_size > context_limit:
                content = self._fit_candidate_content(
                    objective=objective,
                    candidates=candidates,
                    path=relative,
                    content=item.content,
                    settings=settings,
                    context_limit=context_limit,
                    evidence_context=evidence_context,
                    max_chars=per_file,
                )
                if not content:
                    warnings.append("model_patch_context_budget_reached")
                    continue
                next_candidates = [*candidates, {"path": relative, "content": content, "content_complete": False}]
                next_context = self._role_context(objective, next_candidates, settings, evidence_context=evidence_context)
                if len(str(next_context)) > context_limit:
                    warnings.append("model_patch_context_budget_reached")
                    continue
                warnings.append("model_patch_context_truncated_to_role_budget")
            candidates = next_candidates
            remaining = max(0, context_limit - len(str(self._role_context(objective, candidates, settings, evidence_context=evidence_context))))
            if len(candidates) >= max_files or remaining <= 0:
                break
        if len(candidates) < len(eligible_items):
            warnings.append("model_patch_context_limited_to_role_budget")
        return candidates, list(dict.fromkeys(warnings))

    def _role_context(
        self,
        objective: str,
        candidates: list[dict[str, str]],
        settings: dict[str, Any],
        *,
        evidence_context: list[dict[str, Any]] | None = None,
        patch_candidate: PatchCandidateArtifact | None = None,
    ) -> dict[str, Any]:
        context: dict[str, Any] = {
            "objective": self._role_objective(objective, patch_candidate, settings),
            "output_schema": self._output_schema(settings),
        }
        if patch_candidate is not None:
            context["patch_candidate"] = self._role_patch_candidate(patch_candidate, settings)
            current = patch_candidate.current_content_excerpt or next(
                (item["content"] for item in candidates if item["path"] == patch_candidate.target_file),
                "",
            )
            current = self._bounded_text(current, int(settings.get("max_replacement_context_chars", 4200)))
            context["current_content"] = current
            evidence = self._evidence_index(evidence_context or [])
            if evidence:
                context["evidence_refs"] = evidence
            evidence_excerpts = self._replacement_evidence_context(
                evidence_context or [],
                settings,
                objective=objective,
                target_file=patch_candidate.target_file,
                target_symbol=patch_candidate.target_symbol,
            )
            if evidence_excerpts:
                context["evidence"] = evidence_excerpts
            context["proposal_scaffold"] = self._role_proposal_scaffold(
                self._proposal_scaffold(patch_candidate),
                settings,
            )
        else:
            context["files"] = candidates
            evidence = self._evidence_context(evidence_context or [], settings)
            if evidence:
                context["evidence"] = evidence
        return context

    def _role_objective(
        self,
        objective: str,
        patch_candidate: PatchCandidateArtifact | None,
        settings: dict[str, Any],
    ) -> str:
        limit = int(settings.get("max_role_objective_chars", 800))
        if patch_candidate is None:
            return self._bounded_text(objective, limit)
        parts: list[str] = []
        repair_task = (
            patch_candidate.technical_context.get("repair_task")
            if isinstance(patch_candidate.technical_context.get("repair_task"), dict)
            else {}
        )
        for value in (
            patch_candidate.semantic_goal,
            repair_task.get("success_condition"),
            patch_candidate.expected_behavior,
            patch_candidate.replacement_strategy,
        ):
            text = str(value or "").strip()
            if text and text not in parts:
                parts.append(text)
        if not parts:
            return self._bounded_text(objective, limit)
        return self._bounded_text(" ".join(parts), limit)

    def _role_context_limit(self, role_id: str, prompt: str, settings: dict[str, Any]) -> int:
        configured = max(1, int(settings.get("max_context_chars", 48000)))
        bindings = getattr(self.roles, "bindings", None)
        binding = bindings.resolve_binding(role_id) if bindings is not None and hasattr(bindings, "resolve_binding") else None
        if binding is None:
            return configured
        budget = self.budget.calculate(binding, RoleInferenceRequest(role_id=role_id, prompt=prompt, context={}))
        return max(1, min(configured, budget.max_context_chars))

    def _available_content_chars(
        self,
        objective: str,
        candidates: list[dict[str, str]],
        path: str,
        settings: dict[str, Any],
        context_limit: int,
        evidence_context: list[dict[str, Any]],
    ) -> int:
        probe = [*candidates, {"path": path, "content": ""}]
        overhead = len(str(self._role_context(objective, probe, settings, evidence_context=evidence_context)))
        return context_limit - overhead

    def _fit_candidate_content(
        self,
        *,
        objective: str,
        candidates: list[dict[str, str]],
        path: str,
        content: str,
        settings: dict[str, Any],
        context_limit: int,
        evidence_context: list[dict[str, Any]],
        max_chars: int,
    ) -> str:
        upper = min(len(content), max_chars)
        lower = 0
        best = ""
        while lower <= upper:
            midpoint = (lower + upper) // 2
            candidate_content = content[:midpoint]
            probe = [*candidates, {"path": path, "content": candidate_content}]
            size = len(str(self._role_context(objective, probe, settings, evidence_context=evidence_context)))
            if size <= context_limit:
                best = candidate_content
                lower = midpoint + 1
            else:
                upper = midpoint - 1
        minimum = max(200, min(1000, max_chars // 4))
        return best if len(best.strip()) >= minimum else ""

    def _guidance_text(self, objective: str, evidence_context: list[dict[str, Any]]) -> str:
        parts = [objective]
        for item in evidence_context:
            if not isinstance(item, dict):
                continue
            parts.extend(str(item.get(key) or "") for key in ("logical_path", "source_path", "content"))
        return "\n".join(parts).lower()

    def _candidate_priority(self, root: Path, item_path: str, guidance: str) -> tuple[int, int, int]:
        relative = self._relative_candidate_path(root, item_path)
        filename = Path(relative).name.lower() if relative else ""
        normalized = relative.lower().replace("\\", "/")
        wants_validation_target = any(
            marker in guidance
            for marker in (
                "test file",
                "test source",
                "unit test",
                "integration test",
                "arquivo de teste",
                "fonte de teste",
                "teste unitario",
                "teste de integracao",
                "validation test",
                "teste de validacao",
            )
        )
        production_score = 0
        if not wants_validation_target:
            if normalized.startswith("src/main/") or "/src/main/" in normalized:
                production_score = 2
            elif normalized.startswith("src/test/") or "/src/test/" in normalized:
                production_score = -2
        return (
            production_score,
            2 if normalized and normalized in guidance else 1 if filename and filename in guidance else 0,
            -len(relative),
        )

    def _evidence_context(self, evidence_context: list[dict[str, Any]], settings: dict[str, Any]) -> list[dict[str, str]]:
        limit = max(0, int(settings.get("max_evidence_context_chars", 3000) or 3000))
        if limit <= 0:
            return []
        remaining = limit
        result: list[dict[str, str]] = []
        for item in evidence_context:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            excerpt = content[:remaining]
            if not excerpt:
                break
            result.append(
                {
                    "artifact_id": str(item.get("artifact_id") or ""),
                    "logical_path": str(item.get("logical_path") or item.get("source_path") or "artifact"),
                    "excerpt": excerpt,
                }
            )
            remaining -= len(excerpt)
            if remaining <= 0:
                break
        return result

    def _relative_candidate_path(self, root: Path, item_path: str) -> str:
        try:
            path = Path(item_path)
            if path.is_absolute():
                return path.resolve().relative_to(root).as_posix()
            normalized = path.as_posix()
            if not normalized or normalized.startswith("../") or "/../" in normalized:
                return ""
            return normalized
        except (OSError, ValueError):
            return ""

    def _focus_paths_from_evidence(
        self,
        workspace: str,
        evidence_context: list[dict[str, Any]],
        settings: dict[str, Any],
    ) -> list[str]:
        limit = max(0, int(settings.get("max_focus_paths_from_evidence", 24) or 24))
        if limit <= 0:
            return []
        root = Path(workspace).resolve()
        extensions = {
            str(item).casefold()
            for item in settings.get("focus_path_extensions", []) or []
            if str(item).startswith(".")
        }
        if not extensions:
            return []
        pattern = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z0-9_. /\\\\:-]+?\.[A-Za-z0-9_]+)")
        result: list[str] = []
        for item in evidence_context:
            if not isinstance(item, dict):
                continue
            for key in ("source_path", "logical_path", "content"):
                value = str(item.get(key) or "")
                for match in pattern.finditer(value):
                    raw = match.group(1).strip().strip("`'\".,);:]}")
                    path = raw.replace("\\", "/")
                    suffix = Path(path).suffix.casefold()
                    if suffix not in extensions:
                        continue
                    if path.startswith("reports/") or "/reports/" in f"/{path}":
                        continue
                    relative = self._relative_candidate_path(root, path)
                    if not relative:
                        continue
                    if relative not in result:
                        result.append(relative)
                    if len(result) >= limit:
                        return result
        return result

    def _diagnosis_artifact(
        self,
        *,
        workspace: str,
        objective: str,
        source_id: str,
        candidates: list[dict[str, str]],
        evidence_context: list[dict[str, Any]],
    ) -> CanonicalDiagnosisArtifact | None:
        if not candidates:
            return None
        selected = candidates[0]
        target_file = str(selected.get("path") or "")
        target_content = str(selected.get("content") or "")
        if not target_file or not target_content.strip():
            return None
        evidence_refs = [
            str(item.get("artifact_id") or item.get("evidence_id") or item.get("logical_path") or "")
            for item in evidence_context
            if isinstance(item, dict)
        ]
        evidence_refs = [item for item in evidence_refs if item]
        if not evidence_refs:
            evidence_refs = [f"file_context:{source_id}:{target_file}"]
        ranked_evidence = self._rank_evidence_context(objective, evidence_context)
        observed = (
            self._semantic_evidence_summary(
                ranked_evidence,
                objective=objective,
                target_file=target_file,
                target_symbol=target_file,
            )
            or "Current file context was selected for governed patch planning."
        )
        expected = self._diagnosis_expected_behavior(
            objective=objective,
            target_file=target_file,
        )
        semantic_goal = expected or self._bounded_text(target_file, 240) or "Bounded governed patch target."
        repair_strategy = self._diagnosis_repair_strategy(target_file=target_file)
        localization = self._technical_localization(
            workspace=workspace,
            target_file=target_file,
            content=target_content,
            objective=objective,
            evidence_context=ranked_evidence,
        )
        return CanonicalDiagnosisArtifact(
            metadata=DiagnosisMetadata(
                source_type="file_context_bundle",
                source_id=source_id,
                task_run_id=source_id,
            ),
            workspace=workspace,
            semantic_goal=semantic_goal,
            observed_behavior=self._bounded_text(observed, 1200),
            expected_behavior=expected,
            technical_localization=[localization],
            evidence=[
                DiagnosisEvidenceRef(
                    evidence_id=ref,
                    source_type="artifact" if not ref.startswith("file_context:") else "file_context",
                    summary="Evidence selected for governed patch planning.",
                    confidence=0.65,
                )
                for ref in evidence_refs
            ],
            confidence=0.65,
            repair_hints=[
                RepairHint(
                    strategy=repair_strategy,
                    constraints=[
                        "replacement_only",
                        "no_diff_generation",
                        "no_target_selection",
                    ],
                )
            ],
            reason_codes=["diagnosis_derived_from_file_context_bundle"],
        )

    def _diagnosis_expected_behavior(self, *, objective: str, target_file: str) -> str:
        bounded = self._bounded_text(objective, 1200)
        if not bounded or self._looks_operational_expected_behavior(bounded):
            return ""
        target_terms = self._target_terms(target_file)
        if target_terms and not any(term in bounded.replace("\\", "/").casefold() for term in target_terms):
            return ""
        return bounded

    def _diagnosis_repair_strategy(self, *, target_file: str) -> str:
        target = target_file.replace("\\", "/").rsplit("/", 1)[-1] or "the selected target"
        return f"Limit replacement generation to {target} and preserve surrounding contracts unless governed evidence requires a broader canonical patch plan."

    def _technical_localization(
        self,
        *,
        workspace: str,
        target_file: str,
        content: str,
        objective: str,
        evidence_context: list[dict[str, Any]],
    ) -> TechnicalLocalization:
        symbols = self._symbol_candidates(content)
        if not symbols:
            return TechnicalLocalization(
                workspace=workspace,
                target_file=target_file,
                target_symbol=target_file,
                symbol_kind="file",
                confidence=0.65,
            )
        terms = self._evidence_terms(
            objective=objective,
            target_file=target_file,
            target_symbol=Path(target_file).stem,
        )
        best = None
        best_score = 0
        for symbol in symbols:
            snippet = str(symbol.get("snippet") or "").casefold()
            symbol_terms = {
                term
                for term in re.split(r"[/._\-\s]+", str(symbol.get("name") or "").casefold())
                if len(term) >= 3
            }
            score = sum(snippet.count(term) for term in terms if term in snippet)
            score += sum(2 for term in terms if term in symbol_terms)
            if score > best_score:
                best = symbol
                best_score = score
        if not best:
            stem = Path(target_file).stem.casefold()
            best = next(
                (
                    symbol
                    for symbol in symbols
                    if str(symbol.get("kind")) == "class" and str(symbol.get("name") or "").casefold() == stem
                ),
                None,
            )
        if not best:
            return TechnicalLocalization(
                workspace=workspace,
                target_file=target_file,
                target_symbol=target_file,
                symbol_kind="file",
                confidence=0.65,
            )
        return TechnicalLocalization(
            workspace=workspace,
            target_file=target_file,
            target_symbol=str(best.get("name") or target_file),
            symbol_kind=str(best.get("kind") or "file"),
            region_hint=str(best.get("signature") or best.get("name") or ""),
            confidence=0.8 if best_score > 0 else 0.7,
        )

    def _symbol_candidates(self, content: str) -> list[dict[str, str]]:
        lines = str(content or "").splitlines()
        if not lines:
            return []
        patterns = (
            (re.compile(r"^\s*(?:async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("), "function"),
            (re.compile(r"^\s*(?:private\s+|public\s+|internal\s+|override\s+|suspend\s+)*fun\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("), "function"),
            (re.compile(r"^\s*function\s+([A-Za-z_][A-Za-z0-9_]*)\s*\("), "function"),
            (re.compile(r"^\s*class\s+([A-Za-z_][A-Za-z0-9_]*)\b"), "class"),
        )
        results: list[dict[str, str]] = []
        for index, line in enumerate(lines):
            for pattern, kind in patterns:
                match = pattern.search(line)
                if not match:
                    continue
                name = match.group(1)
                window = "\n".join(lines[index : min(len(lines), index + 32)])
                results.append(
                    {
                        "name": name,
                        "kind": kind,
                        "signature": line.strip(),
                        "snippet": window,
                    }
                )
                break
        return results

    def _looks_operational_expected_behavior(self, value: str) -> bool:
        text = str(value or "").replace("\\", "/").casefold()
        if not text:
            return False
        markers = {
            "artifact",
            "artifacts",
            "approval",
            "completion",
            "contract",
            "diff",
            "fase",
            "generate",
            "gerar",
            "patch plan",
            "patch planning",
            "patch preview",
            "phase",
            "report",
            "reports/",
            "responder",
            "rollback",
            "speaker truth",
            "success contract",
            "task run",
            "taskrun",
            "validation",
        }
        marker_count = sum(1 for marker in markers if marker in text)
        artifact_shape = bool(re.search(r"(^|[/\s])[^/\s]+\.(md|csv|json|zip)\b", text))
        return marker_count >= 2 or (artifact_shape and marker_count >= 1)

    def _target_terms(self, target_file: str) -> set[str]:
        normalized = str(target_file or "").replace("\\", "/").casefold()
        if not normalized:
            return set()
        terms = {normalized}
        filename = normalized.rsplit("/", 1)[-1]
        if filename:
            terms.add(filename)
            stem = filename.rsplit(".", 1)[0]
            if stem:
                terms.add(stem)
        return {term for term in terms if len(term) >= 3}

    def _role_patch_candidate(
        self,
        patch_candidate: PatchCandidateArtifact,
        settings: dict[str, Any],
    ) -> dict[str, Any]:
        field_limit = int(settings.get("max_candidate_field_chars", 800))
        payload = patch_candidate.model_dump(mode="json")
        payload.pop("current_content_excerpt", None)
        candidate_transformation_payload = payload.pop("candidate_transformation", None)
        for key in ("semantic_goal", "observed_behavior", "expected_behavior", "replacement_strategy"):
            payload[key] = self._bounded_text(str(payload.get(key) or ""), field_limit)
        payload["optional_constraints"] = [
            self._bounded_text(str(item), field_limit)
            for item in list(payload.get("optional_constraints") or [])[:4]
        ]
        payload["evidence_refs"] = list(payload.get("evidence_refs") or [])[:4]
        if isinstance(candidate_transformation_payload, dict):
            payload["candidate_transformation"] = {
                "status": candidate_transformation_payload.get("status"),
                "coverage_score": candidate_transformation_payload.get("coverage_score"),
                "behavior_summary": self._bounded_text(str(candidate_transformation_payload.get("behavior_summary") or ""), field_limit),
                "transformation_strategy": self._bounded_text(
                    str(candidate_transformation_payload.get("transformation_strategy") or ""),
                    field_limit,
                ),
                "success_criteria": [
                    self._bounded_text(str(item), field_limit)
                    for item in list(candidate_transformation_payload.get("success_criteria") or [])[:3]
                ],
            }
        technical_context = payload.get("technical_context")
        if isinstance(technical_context, dict):
            actionability = technical_context.get("actionability") if isinstance(technical_context.get("actionability"), dict) else {}
            repair_task = technical_context.get("repair_task") if isinstance(technical_context.get("repair_task"), dict) else {}
            repair_intent = technical_context.get("repair_intent") if isinstance(technical_context.get("repair_intent"), dict) else {}
            alignment = technical_context.get("alignment") if isinstance(technical_context.get("alignment"), dict) else {}
            semantic_evidence = technical_context.get("semantic_evidence") if isinstance(technical_context.get("semantic_evidence"), dict) else {}
            behavior_localization = technical_context.get("behavior_localization") if isinstance(technical_context.get("behavior_localization"), dict) else {}
            behavior_justification = technical_context.get("behavior_justification") if isinstance(technical_context.get("behavior_justification"), dict) else {}
            candidate_transformation = technical_context.get("candidate_transformation") if isinstance(technical_context.get("candidate_transformation"), dict) else {}
            payload["technical_context"] = {
                "region_hint": technical_context.get("region_hint"),
                "diagnosis_type": technical_context.get("diagnosis_type"),
                "current_content_complete": technical_context.get("current_content_complete"),
                "current_content_chars": technical_context.get("current_content_chars"),
                "source_content_chars": technical_context.get("source_content_chars"),
                "actionability": {
                    "score": actionability.get("score"),
                    "editable": actionability.get("editable"),
                    "edit_unit": actionability.get("edit_unit"),
                },
                "alignment": {
                    "score": alignment.get("score"),
                    "aligned": alignment.get("aligned"),
                    "gaps": list(alignment.get("gaps") or []),
                    "reason_codes": list(alignment.get("reason_codes") or []),
                },
                "repair_task": {
                    "repair_task_id": repair_task.get("repair_task_id"),
                    "actionable": repair_task.get("actionable"),
                    "edit_unit": repair_task.get("edit_unit"),
                    "behavior_to_create": self._bounded_text(str(repair_task.get("behavior_to_create") or ""), field_limit),
                    "success_condition": self._bounded_text(str(repair_task.get("success_condition") or ""), field_limit),
                    "repair_boundary": [
                        self._bounded_text(str(item), field_limit)
                        for item in list(repair_task.get("repair_boundary") or [])[:6]
                    ],
                    "gaps": list(repair_task.get("gaps") or []),
                },
                "repair_intent": {
                    "target_file": repair_intent.get("target_file"),
                    "target_symbol": repair_intent.get("target_symbol"),
                    "expected_behavior": self._bounded_text(str(repair_intent.get("expected_behavior") or ""), field_limit),
                    "success_condition": self._bounded_text(str(repair_intent.get("success_condition") or ""), field_limit),
                    "repair_boundary": [
                        self._bounded_text(str(item), field_limit)
                        for item in list(repair_intent.get("repair_boundary") or [])[:8]
                    ],
                    "reason_codes": list(repair_intent.get("reason_codes") or []),
                },
                "semantic_evidence": {
                    "coverage_score": semantic_evidence.get("coverage_score"),
                    "status": semantic_evidence.get("status"),
                    "diagnostics": list(semantic_evidence.get("diagnostics") or []),
                },
                "behavior_localization": {
                    "coverage_score": behavior_localization.get("coverage_score"),
                    "status": behavior_localization.get("status"),
                    "anchor_kind": behavior_localization.get("anchor_kind"),
                    "anchor_name": behavior_localization.get("anchor_name"),
                },
                "behavior_justification": {
                    "coverage_score": behavior_justification.get("coverage_score"),
                    "status": behavior_justification.get("status"),
                    "reasoning_chain": [
                        self._bounded_text(str(item), field_limit)
                        for item in list(behavior_justification.get("reasoning_chain") or [])[:4]
                    ],
                },
                "candidate_transformation": {
                    "coverage_score": candidate_transformation.get("coverage_score"),
                    "status": candidate_transformation.get("status"),
                    "behavior_summary": self._bounded_text(str(candidate_transformation.get("behavior_summary") or ""), field_limit),
                    "success_criteria": [
                        self._bounded_text(str(item), field_limit)
                        for item in list(candidate_transformation.get("success_criteria") or [])[:4]
                    ],
                    "constraints": [
                        self._bounded_text(str(item), field_limit)
                        for item in list(candidate_transformation.get("constraints") or [])[:6]
                    ],
                    "invariants": [
                        self._bounded_text(str(item), field_limit)
                        for item in list(candidate_transformation.get("invariants") or [])[:6]
                    ],
                },
            }
        return payload

    def _role_proposal_scaffold(
        self,
        proposal: RepairProposalArtifact,
        settings: dict[str, Any],
    ) -> dict[str, Any]:
        field_limit = int(settings.get("max_candidate_field_chars", 800))
        return {
            "proposal_status": proposal.proposal_status,
            "proposal_completeness": proposal.proposal_completeness,
            "target": {
                "workspace": proposal.target.workspace,
                "file": proposal.target.file,
                "symbol": proposal.target.symbol,
                "symbol_kind": proposal.target.symbol_kind,
            },
            "intent": self._bounded_text(proposal.intent, field_limit),
            "concrete_change": {
                "objective": self._bounded_text(proposal.concrete_change.objective, field_limit),
                "current_behavior": self._bounded_text(proposal.concrete_change.current_behavior, field_limit),
                "expected_behavior": self._bounded_text(proposal.concrete_change.expected_behavior, field_limit),
                "behavior_summary": self._bounded_text(proposal.concrete_change.behavior_summary, field_limit),
                "modification_strategy": self._bounded_text(proposal.concrete_change.modification_strategy, field_limit),
                "affected_symbols": list(proposal.concrete_change.affected_symbols[:6]),
                "constraints": [
                    self._bounded_text(str(item), field_limit)
                    for item in proposal.concrete_change.constraints[:4]
                ],
                "invariants": [
                    self._bounded_text(str(item), field_limit)
                    for item in proposal.concrete_change.invariants[:4]
                ],
                "success_criteria": [
                    self._bounded_text(str(item), field_limit)
                    for item in proposal.concrete_change.success_criteria[:4]
                ],
            },
            "assembly": {
                "status": proposal.assembly.assembly_status,
                "score": proposal.assembly.assembly_score,
                "semantic_evidence": {
                    "status": proposal.assembly.semantic_evidence.status,
                    "coverage_score": proposal.assembly.semantic_evidence.coverage_score,
                },
                "behavior_localization": {
                    "status": proposal.assembly.behavior_localization.status,
                    "coverage_score": proposal.assembly.behavior_localization.coverage_score,
                },
                "behavior_justification": {
                    "status": proposal.assembly.behavior_justification.status,
                    "coverage_score": proposal.assembly.behavior_justification.coverage_score,
                },
                "candidate_transformation": {
                    "status": proposal.assembly.candidate_transformation.status,
                    "coverage_score": proposal.assembly.candidate_transformation.coverage_score,
                },
            },
            "diagnostics": [
                self._bounded_text(str(item), field_limit)
                for item in proposal.diagnostics[:4]
            ],
        }

    def _evidence_index(self, evidence_context: list[dict[str, Any]]) -> list[dict[str, str]]:
        result: list[dict[str, str]] = []
        for item in evidence_context:
            if not isinstance(item, dict):
                continue
            result.append(
                {
                    "artifact_id": str(item.get("artifact_id") or ""),
                    "logical_path": str(item.get("logical_path") or item.get("source_path") or "artifact"),
                }
            )
        return result

    def _replacement_evidence_context(
        self,
        evidence_context: list[dict[str, Any]],
        settings: dict[str, Any],
        *,
        objective: str = "",
        target_file: str = "",
        target_symbol: str = "",
    ) -> list[dict[str, str]]:
        limit = max(0, int(settings.get("max_replacement_evidence_context_chars", 1400) or 1400))
        if limit <= 0:
            return []
        remaining = limit
        result: list[dict[str, str]] = []
        terms = self._evidence_terms(objective=objective, target_file=target_file, target_symbol=target_symbol)
        for item in evidence_context:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            excerpt = self._relevant_excerpt(content, terms, remaining)
            if not excerpt:
                break
            result.append(
                {
                    "artifact_id": str(item.get("artifact_id") or ""),
                    "logical_path": str(item.get("logical_path") or item.get("source_path") or "artifact"),
                    "excerpt": excerpt,
                }
            )
            remaining -= len(excerpt)
            if remaining <= 0:
                break
        return result

    def _fit_role_context_to_budget(self, context: dict[str, Any], context_limit: int) -> dict[str, Any]:
        # The serialized role payload grows faster than the effective prompt budget.
        # Keep a conservative cap so structured scaffolds and evidence remain bounded.
        context_limit = min(context_limit, 7800)
        if len(str(context)) <= context_limit:
            return context
        fitted = dict(context)
        patch_candidate = fitted.get("patch_candidate")
        target_file = ""
        target_symbol = ""
        if isinstance(patch_candidate, dict):
            target_file = str(patch_candidate.get("target_file") or "")
            target_symbol = str(patch_candidate.get("target_symbol") or "")
        evidence_terms = self._evidence_terms(
            objective=str(fitted.get("objective") or ""),
            target_file=target_file,
            target_symbol=target_symbol,
        )
        evidence_refs = list(fitted.get("evidence_refs") or [])
        while evidence_refs and len(str(fitted)) > context_limit:
            if len(evidence_refs) > 1:
                evidence_refs.pop()
                fitted["evidence_refs"] = evidence_refs
            else:
                break
        evidence = list(fitted.get("evidence") or [])
        while evidence and len(str(fitted)) > context_limit:
            item = dict(evidence[-1])
            excerpt = str(item.get("excerpt") or "")
            if len(excerpt) > 200:
                new_limit = max(200, len(excerpt) // 2)
                item["excerpt"] = self._relevant_excerpt(excerpt, evidence_terms, new_limit)
                evidence[-1] = item
                fitted["evidence"] = evidence
            elif len(evidence) > 1:
                evidence.pop()
                fitted["evidence"] = evidence
            else:
                break
        candidate = fitted.get("patch_candidate")
        if isinstance(candidate, dict):
            compact_candidate = dict(candidate)
            technical_context = compact_candidate.get("technical_context")
            if isinstance(technical_context, dict):
                repair_task = technical_context.get("repair_task")
                if isinstance(repair_task, dict) and len(str(fitted)) > context_limit:
                    repair_task = dict(repair_task)
                    repair_task["repair_boundary"] = list(repair_task.get("repair_boundary") or [])[:3]
                    repair_task["gaps"] = list(repair_task.get("gaps") or [])[:3]
                    technical_context["repair_task"] = repair_task
                repair_intent = technical_context.get("repair_intent")
                if isinstance(repair_intent, dict) and len(str(fitted)) > context_limit:
                    repair_intent = dict(repair_intent)
                    repair_intent["repair_boundary"] = list(repair_intent.get("repair_boundary") or [])[:3]
                    technical_context["repair_intent"] = repair_intent
                alignment = technical_context.get("alignment")
                if isinstance(alignment, dict) and len(str(fitted)) > context_limit:
                    alignment = dict(alignment)
                    alignment.pop("reason_codes", None)
                    alignment["gaps"] = list(alignment.get("gaps") or [])[:2]
                    technical_context["alignment"] = alignment
                proposal_bits = ("behavior_justification", "candidate_transformation")
                for key in proposal_bits:
                    block = technical_context.get(key)
                    if isinstance(block, dict) and len(str(fitted)) > context_limit:
                        compact_block = dict(block)
                        compact_block.pop("diagnostics", None)
                        compact_block["constraints"] = list(compact_block.get("constraints") or [])[:2]
                        compact_block["invariants"] = list(compact_block.get("invariants") or [])[:2]
                        compact_block["success_criteria"] = list(compact_block.get("success_criteria") or [])[:2]
                        compact_block["reasoning_chain"] = list(compact_block.get("reasoning_chain") or [])[:2]
                        technical_context[key] = compact_block
                compact_candidate["technical_context"] = technical_context
                fitted["patch_candidate"] = compact_candidate
            for key in ("observed_behavior", "semantic_goal", "expected_behavior", "replacement_strategy"):
                while len(str(fitted)) > context_limit and len(str(compact_candidate.get(key) or "")) > 120:
                    compact_candidate[key] = str(compact_candidate.get(key) or "")[:120]
                    if key == "expected_behavior":
                        technical_context = compact_candidate.get("technical_context")
                        if isinstance(technical_context, dict):
                            repair_intent = technical_context.get("repair_intent")
                            if isinstance(repair_intent, dict):
                                repair_intent = dict(repair_intent)
                                repair_intent["expected_behavior"] = compact_candidate[key]
                                technical_context["repair_intent"] = repair_intent
                                compact_candidate["technical_context"] = technical_context
                    fitted["patch_candidate"] = compact_candidate
        scaffold = fitted.get("proposal_scaffold")
        if isinstance(scaffold, dict):
            compact_scaffold = dict(scaffold)
            while len(str(fitted)) > context_limit and compact_scaffold.get("diagnostics"):
                diagnostics = list(compact_scaffold.get("diagnostics") or [])
                diagnostics.pop()
                compact_scaffold["diagnostics"] = diagnostics
                fitted["proposal_scaffold"] = compact_scaffold
            concrete = compact_scaffold.get("concrete_change")
            if isinstance(concrete, dict):
                for key in ("current_behavior", "expected_behavior", "objective", "modification_strategy"):
                    while len(str(fitted)) > context_limit and len(str(concrete.get(key) or "")) > 120:
                        concrete[key] = str(concrete.get(key) or "")[:120]
                        compact_scaffold["concrete_change"] = concrete
                        fitted["proposal_scaffold"] = compact_scaffold
                while len(str(fitted)) > context_limit and len(list(concrete.get("affected_symbols") or [])) > 1:
                    affected_symbols = list(concrete.get("affected_symbols") or [])
                    affected_symbols.pop()
                    concrete["affected_symbols"] = affected_symbols
                    compact_scaffold["concrete_change"] = concrete
                    fitted["proposal_scaffold"] = compact_scaffold
        objective = str(fitted.get("objective") or "")
        while objective and len(str(fitted)) > context_limit and len(objective) > 120:
            objective = objective[: max(120, len(objective) - max(128, (len(str(fitted)) - context_limit) + 32))]
            fitted["objective"] = objective
        if len(str(fitted)) > context_limit and isinstance(candidate, dict):
            compact_candidate = dict(fitted.get("patch_candidate") or {})
            technical_context = compact_candidate.get("technical_context")
            if isinstance(technical_context, dict):
                for key in ("semantic_evidence", "behavior_justification", "candidate_transformation"):
                    if key in technical_context and len(str(fitted)) > context_limit:
                        technical_context.pop(key, None)
                        compact_candidate["technical_context"] = technical_context
                        fitted["patch_candidate"] = compact_candidate
        if len(str(fitted)) > context_limit and isinstance(scaffold, dict):
            compact_scaffold = dict(fitted.get("proposal_scaffold") or {})
            concrete = compact_scaffold.get("concrete_change")
            if isinstance(concrete, dict):
                for key in ("current_behavior", "objective", "modification_strategy"):
                    if key in concrete and len(str(fitted)) > context_limit:
                        concrete.pop(key, None)
                        compact_scaffold["concrete_change"] = concrete
                        fitted["proposal_scaffold"] = compact_scaffold
            if len(str(fitted)) > context_limit:
                compact_scaffold.pop("diagnostics", None)
                fitted["proposal_scaffold"] = compact_scaffold
        if len(str(fitted)) > context_limit and isinstance(candidate, dict):
            compact_candidate = dict(fitted.get("patch_candidate") or {})
            technical_context = compact_candidate.get("technical_context")
            if isinstance(technical_context, dict):
                repair_intent = technical_context.get("repair_intent")
                minimal_context: dict[str, Any] = {}
                if isinstance(repair_intent, dict):
                    minimal_context["repair_intent"] = repair_intent
                actionability = technical_context.get("actionability")
                if isinstance(actionability, dict):
                    minimal_context["actionability"] = {
                        "score": actionability.get("score"),
                        "editable": actionability.get("editable"),
                    }
                alignment = technical_context.get("alignment")
                if isinstance(alignment, dict):
                    minimal_context["alignment"] = {
                        "score": alignment.get("score"),
                        "aligned": alignment.get("aligned"),
                    }
                compact_candidate["technical_context"] = minimal_context
                fitted["patch_candidate"] = compact_candidate
        current = str(fitted.get("current_content") or "")
        while current and len(str(fitted)) > context_limit:
            minimum = max(200, min(len(current), 800))
            if len(current) <= minimum:
                break
            current = current[: max(0, len(current) - max(256, (len(str(fitted)) - context_limit) + 64))]
            fitted["current_content"] = current
        return fitted

    def _mark_candidate_context_completeness(
        self,
        patch_candidate: PatchCandidateArtifact,
        candidates: list[dict[str, Any]],
        context: dict[str, Any],
    ) -> None:
        source = next((item for item in candidates if item.get("path") == patch_candidate.target_file), None)
        source_content = str((source or {}).get("content") or "")
        current_content = str(context.get("current_content") or "")
        source_complete = bool((source or {}).get("content_complete", True))
        complete = bool(source_complete and source_content and current_content == source_content)
        patch_candidate.technical_context = {
            **dict(patch_candidate.technical_context),
            "current_content_complete": complete,
            "current_content_chars": len(current_content),
            "source_content_chars": len(source_content),
        }

    def _rank_evidence_context(self, objective: str, evidence_context: list[dict[str, Any]]) -> list[dict[str, Any]]:
        guidance = str(objective or "").casefold()
        relevance_terms = {
            "analysis",
            "diagnosis",
            "diagnostico",
            "diff",
            "risk",
            "risco",
            "comparison",
            "comparacao",
            "experimental",
            "static",
            "patch",
            "preview",
            "hypothesis",
            "hipotese",
        }

        def score(item: dict[str, Any]) -> tuple[int, int, str]:
            logical = str(item.get("logical_path") or item.get("source_path") or "").casefold()
            content = str(item.get("content") or "").casefold()
            combined = f"{logical}\n{content[:1200]}"
            objective_hits = sum(1 for token in set(re.findall(r"[a-z0-9_]{4,}", guidance)) if token in combined)
            relevance_hits = sum(1 for token in relevance_terms if token in combined)
            return (relevance_hits, objective_hits, logical)

        valid = [item for item in evidence_context if isinstance(item, dict)]
        return sorted(valid, key=score, reverse=True)

    def _semantic_evidence_summary(
        self,
        evidence_context: list[dict[str, Any]],
        *,
        objective: str = "",
        target_file: str = "",
        target_symbol: str = "",
    ) -> str:
        parts: list[str] = []
        terms = self._evidence_terms(objective=objective, target_file=target_file, target_symbol=target_symbol)
        for item in evidence_context[:3]:
            logical = str(item.get("logical_path") or item.get("source_path") or "artifact")
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            parts.append(f"{logical}\n{self._relevant_excerpt(content, terms, 500)}")
        return "\n\n".join(parts)

    def _evidence_terms(self, *, objective: str = "", target_file: str = "", target_symbol: str = "") -> list[str]:
        raw_terms: list[str] = []
        for value in (target_file, target_symbol):
            normalized = str(value or "").replace("\\", "/").casefold()
            if normalized:
                raw_terms.append(normalized)
                raw_terms.append(Path(normalized).name)
                raw_terms.append(Path(normalized).stem)
                raw_terms.extend(part for part in re.split(r"[/._\-]+", normalized) if len(part) >= 4)
        raw_terms.extend(
            token
            for token in re.findall(r"[A-Za-z0-9_]{4,}", str(objective or "").casefold())
            if token not in {"phase", "fase", "reports", "artifact", "artifacts", "obrigatorios"}
        )
        result: list[str] = []
        for term in raw_terms:
            term = term.strip().casefold()
            if len(term) < 4 or term in result:
                continue
            result.append(term)
        return result

    def _relevant_excerpt(self, content: str, terms: list[str], limit: int) -> str:
        text = str(content or "")
        if limit <= 0:
            return ""
        if len(text) <= limit:
            return text
        lowered = text.casefold()
        indexes: list[int] = []
        for term in terms:
            index = lowered.find(term.casefold())
            if index >= 0:
                indexes.append(index)
        if not indexes:
            return text[:limit]
        best_start = 0
        best_score = -1
        for index in indexes:
            start = max(0, min(index - limit // 3, len(text) - limit))
            window = lowered[start : start + limit]
            score = sum(window.count(term.casefold()) for term in terms)
            if score > best_score or (score == best_score and start < best_start):
                best_score = score
                best_start = start
        prefix = "[excerpt]\n" if best_start > 0 else ""
        excerpt_limit = max(0, limit - len(prefix))
        return prefix + text[best_start : best_start + excerpt_limit]

    def _bounded_text(self, value: str, limit: int) -> str:
        text = str(value or "")
        if limit <= 0 or len(text) <= limit:
            return text
        return text[:limit].rstrip() + "\n[truncated]"

    def _proposal_prompt(self) -> str:
        return (
            "Return one JSON RepairProposal object for the supplied patch candidate. "
            "Do not choose files, paths, hunks, diffs, tools, approval, or execution. "
            "Do not claim success. Use only current_content, constraints, and evidence. "
            "Treat proposal_scaffold as the canonical runtime-compiled baseline and refine only the fields that require technical judgment. "
            "The Runtime owns validation, preview rendering, rollback governance, and compilation. "
            "You must fill a structured proposal with target, intent, concrete_change, rollback, impact, risks, and optional confidence. "
            "The concrete_change must describe the smallest meaningful edit for the selected target. "
            "If you can express the change precisely, include suggested_replacement inside concrete_change as the full replacement text for the selected edit unit. "
            "If evidence is insufficient for a precise replacement, leave suggested_replacement empty but still provide the structured repair proposal. "
            "Do not refuse solely because the operation is planning/read-only or because approval is still required."
        )

    def _output_schema(self, settings: dict[str, Any]) -> dict[str, Any]:
        output = settings.get("output", {})
        return output if isinstance(output, dict) else {}

    def _accepted_model_run(self, model_run: Any, settings: dict[str, Any]) -> bool:
        if bool(settings.get("require_completed_model_run", True)) and model_run.status != "completed":
            return False
        if not bool(settings.get("allow_fallback_output", False)) and bool(model_run.fallback_used):
            return False
        return bool(model_run.output.strip())

    def _parse_repair_proposal(
        self,
        output: str,
        patch_candidate: PatchCandidateArtifact,
    ) -> tuple[RepairProposalArtifact | None, str | None]:
        decoder = json.JSONDecoder()
        for index, character in enumerate(output):
            if character != "{":
                continue
            try:
                payload, _ = decoder.raw_decode(output[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict) and "edits" in payload:
                legacy, error = self._parse_legacy_edit(payload, patch_candidate)
                if legacy is not None:
                    return legacy, None
                return None, error
            try:
                proposal = RepairProposalArtifact(**payload)
            except (TypeError, ValueError):
                legacy, error = self._parse_legacy_replacement(payload, patch_candidate)
                if legacy is not None:
                    return legacy, None
                return None, error or "PATCH_REPLACEMENT_INVALID"
            return proposal, None
        return None, "PATCH_REPLACEMENT_INVALID"

    def _parse_legacy_edit(
        self,
        payload: dict[str, Any],
        patch_candidate: PatchCandidateArtifact,
    ) -> tuple[RepairProposalArtifact | None, str | None]:
        try:
            proposal = ModelPatchProposal(**payload)
        except (TypeError, ValueError):
            return None, "PATCH_REPLACEMENT_INVALID"
        if not proposal.edits:
            return None, "PATCH_MODEL_EMPTY_OUTPUT"
        edit = proposal.edits[0]
        return self._repair_proposal_from_legacy(
            patch_candidate,
            replacement=edit.replacement,
            rationale=edit.rationale or edit.evidence_excerpt,
            confidence=0.5,
        ), None

    def _parse_legacy_replacement(
        self,
        payload: dict[str, Any],
        patch_candidate: PatchCandidateArtifact,
    ) -> tuple[RepairProposalArtifact | None, str | None]:
        try:
            proposal = ModelReplacementProposal(**payload)
        except (TypeError, ValueError):
            return None, "PATCH_REPLACEMENT_INVALID"
        if not (proposal.replacement or proposal.patch_snippet or proposal.rationale):
            return None, "PATCH_MODEL_EMPTY_OUTPUT"
        if not (proposal.replacement or proposal.patch_snippet):
            return None, "PATCH_MODEL_EMPTY_OUTPUT"
        return self._repair_proposal_from_legacy(
            patch_candidate,
            replacement=proposal.replacement or proposal.patch_snippet,
            rationale=proposal.rationale,
            confidence=proposal.confidence,
        ), None

    def _repair_proposal_from_legacy(
        self,
        patch_candidate: PatchCandidateArtifact,
        *,
        replacement: str,
        rationale: str,
        confidence: float,
    ) -> RepairProposalArtifact:
        affected_symbols = [patch_candidate.target_symbol] if patch_candidate.target_symbol else []
        affected_modules = [Path(patch_candidate.target_file).parent.as_posix() or patch_candidate.target_file]
        rollback_symbols = list(affected_symbols)
        runtime_behavior = patch_candidate.expected_behavior or patch_candidate.semantic_goal
        risk_level = patch_candidate.risk_level or "medium"
        return RepairProposalArtifact(
            diagnosis_id=patch_candidate.diagnosis_id,
            candidate_id=patch_candidate.candidate_id,
            task_run_id=patch_candidate.task_run_id,
            execution_plan_id=patch_candidate.execution_plan_id,
            target=RepairProposalTarget(
                workspace=patch_candidate.workspace,
                file=patch_candidate.target_file,
                symbol=patch_candidate.target_symbol,
                symbol_kind=patch_candidate.symbol_kind,
            ),
            intent=patch_candidate.semantic_goal or "repair_target_behavior",
            concrete_change=RepairProposalConcreteChange(
                objective=patch_candidate.semantic_goal or "Repair the selected target behavior.",
                current_behavior=patch_candidate.observed_behavior,
                expected_behavior=patch_candidate.expected_behavior,
                modification_strategy=rationale or patch_candidate.replacement_strategy or "Apply a focused replacement in the selected edit unit.",
                affected_symbols=affected_symbols,
                reasoning=rationale or "Legacy replacement adapted into canonical repair proposal.",
                suggested_replacement=replacement,
            ),
            rollback=RepairProposalRollback(
                possible=True,
                strategy="Revert only the selected edit unit if validation or regression checks fail.",
                affected_symbols=rollback_symbols,
                side_effects=["Behavior may return to the pre-repair state until a safer proposal is available."],
            ),
            impact=RepairProposalImpact(
                scope="focused_edit_unit",
                affected_modules=affected_modules,
                runtime_behavior=runtime_behavior,
                compatibility="Preserve existing public contracts and limit changes to the selected target.",
                risk_level=risk_level,
            ),
            risks=RepairProposalRisks(
                technical=["Replacement may need reconciliation with neighboring code outside the selected unit."],
                behavioral=["The repaired behavior must be validated against the observed failing path and an existing working path."],
                regression=["Adjacent call sites or format variations can regress if assumptions in the selected unit are incomplete."],
                confidence="media" if confidence >= 0.5 else "baixa",
            ),
            confidence=confidence,
            evidence_refs=list(patch_candidate.evidence_refs),
            warnings=["legacy_repair_proposal_adapter_used"],
        )

    def _proposal_scaffold(self, patch_candidate: PatchCandidateArtifact) -> RepairProposalArtifact:
        return self.proposal_compiler.compile(patch_candidate)

    def _merge_repair_proposal(
        self,
        proposal: RepairProposalArtifact,
        patch_candidate: PatchCandidateArtifact,
    ) -> RepairProposalArtifact:
        return self.proposal_compiler.merge(proposal, patch_candidate)

    def _partial_repair_proposal(
        self,
        patch_candidate: PatchCandidateArtifact,
        *,
        warning: str,
    ) -> RepairProposalArtifact:
        return self.proposal_compiler.partial(patch_candidate, warning=warning)

    def _proposal_assembly(self, patch_candidate: PatchCandidateArtifact) -> RepairProposalAssembly:
        technical_context = dict(patch_candidate.technical_context)
        return RepairProposalAssembly(
            semantic_evidence=self._proposal_assembly_stage(technical_context.get("semantic_evidence")),
            behavior_localization=self._proposal_assembly_stage(technical_context.get("behavior_localization")),
            behavior_justification=self._proposal_assembly_stage(technical_context.get("behavior_justification")),
            candidate_transformation=self._proposal_assembly_stage(
                technical_context.get("candidate_transformation")
                or (patch_candidate.candidate_transformation.model_dump(mode="json") if patch_candidate.candidate_transformation else {})
            ),
        )

    def _proposal_assembly_stage(self, payload: Any) -> RepairProposalAssemblyStage:
        block = dict(payload) if isinstance(payload, dict) else {}
        return RepairProposalAssemblyStage(
            artifact_id=str(block.get("artifact_id") or ""),
            status=str(block.get("status") or "missing"),
            coverage_score=int(block.get("coverage_score") or 0),
            confidence=float(block.get("confidence") or 0.0),
            reason_codes=[str(item) for item in list(block.get("reason_codes") or []) if str(item).strip()],
            diagnostics=[str(item) for item in list(block.get("diagnostics") or []) if str(item).strip()],
        )

    def _merge_proposal_assembly(
        self,
        proposal: RepairProposalAssembly,
        scaffold: RepairProposalAssembly,
    ) -> RepairProposalAssembly:
        return RepairProposalAssembly(
            semantic_evidence=self._merge_proposal_assembly_stage(proposal.semantic_evidence, scaffold.semantic_evidence),
            behavior_localization=self._merge_proposal_assembly_stage(proposal.behavior_localization, scaffold.behavior_localization),
            behavior_justification=self._merge_proposal_assembly_stage(proposal.behavior_justification, scaffold.behavior_justification),
            candidate_transformation=self._merge_proposal_assembly_stage(proposal.candidate_transformation, scaffold.candidate_transformation),
        )

    def _merge_proposal_assembly_stage(
        self,
        proposal: RepairProposalAssemblyStage,
        scaffold: RepairProposalAssemblyStage,
    ) -> RepairProposalAssemblyStage:
        merged = proposal.model_copy(
            update={
                "artifact_id": proposal.artifact_id or scaffold.artifact_id,
                "status": proposal.status if proposal.status != "missing" else scaffold.status,
                "coverage_score": proposal.coverage_score or scaffold.coverage_score,
                "confidence": proposal.confidence or scaffold.confidence,
                "reason_codes": list(dict.fromkeys([*scaffold.reason_codes, *proposal.reason_codes])),
                "diagnostics": list(dict.fromkeys([*scaffold.diagnostics, *proposal.diagnostics])),
            }
        )
        return merged

    def _validate_repair_proposal(
        self,
        proposal: RepairProposalArtifact,
        patch_candidate: PatchCandidateArtifact,
    ) -> list[str]:
        errors = list(proposal.missing_reason_codes())
        if proposal.target.file.replace("\\", "/") != patch_candidate.target_file.replace("\\", "/"):
            errors.append("PROPOSAL_TARGET_MISSING")
        if patch_candidate.target_symbol and proposal.target.symbol != patch_candidate.target_symbol:
            errors.append("PROPOSAL_SYMBOLS_MISSING")
        current_behavior = proposal.concrete_change.current_behavior.strip().casefold()
        observed_behavior = patch_candidate.observed_behavior.strip().casefold()
        if (
            observed_behavior
            and current_behavior
            and self._behavior_representation_matches(observed_behavior, current_behavior)
            and observed_behavior not in current_behavior
            and current_behavior not in observed_behavior
        ):
            errors.extend(["PROPOSAL_BEHAVIOR_MISSING", "PROPOSAL_CONCRETE_CHANGE_MISSING"])
        return list(dict.fromkeys(errors))

    def _behavior_representation_matches(self, observed_behavior: str, current_behavior: str) -> bool:
        return self._looks_like_code_fragment(observed_behavior) == self._looks_like_code_fragment(current_behavior)

    def _looks_like_code_fragment(self, value: str) -> bool:
        text = value.strip()
        if not text:
            return False
        if "\n" in text:
            return True
        if re.search(r"[{}();=\[\]]", text):
            return True
        if re.search(r"\b(def|class|fun|return|const|let|var)\b", text):
            return True
        if re.search(r"\b[A-Za-z_][A-Za-z0-9_]*\s*\(", text):
            return True
        if re.search(r"[\"'].*[\"']", text):
            return True
        return False

    def _validate_replacement(
        self,
        replacement: str,
        patch_candidate: PatchCandidateArtifact,
        candidates: list[dict[str, str]],
    ) -> str | None:
        known = {item["path"]: item["content"] for item in candidates}
        if patch_candidate.target_file not in known:
            return "PATCH_CANDIDATE_INSUFFICIENT"
        if not replacement.strip():
            return "PATCH_MODEL_EMPTY_OUTPUT"
        if patch_candidate.symbol_kind == "file" and not bool(patch_candidate.technical_context.get("current_content_complete", False)):
            return "PATCH_CONTEXT_TOO_SMALL"
        if replacement == known[patch_candidate.target_file]:
            return "PATCH_REPLACEMENT_INVALID"
        return None
