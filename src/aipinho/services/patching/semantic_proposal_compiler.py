from __future__ import annotations

from pathlib import Path

from aipinho.schemas.patching.patch_candidate_artifact import PatchCandidateArtifact
from aipinho.schemas.patching.repair_proposal_artifact import (
    RepairProposalArtifact,
    RepairProposalAssembly,
    RepairProposalAssemblyStage,
    RepairProposalConcreteChange,
    RepairProposalImpact,
    RepairProposalRisks,
    RepairProposalRollback,
    RepairProposalTarget,
)


class SemanticProposalCompiler:
    """Compiles deterministic, incremental repair proposals from repair candidates.

    This service does not execute patches, generate diffs, or decide approval.
    Its only responsibility is to turn governed repair understanding into a
    canonical proposal artifact that can be enriched incrementally.
    """

    def compile(self, patch_candidate: PatchCandidateArtifact) -> RepairProposalArtifact:
        technical_context = dict(patch_candidate.technical_context)
        repair_task = technical_context.get("repair_task") if isinstance(technical_context.get("repair_task"), dict) else {}
        transformation = (
            technical_context.get("candidate_transformation")
            if isinstance(technical_context.get("candidate_transformation"), dict)
            else {}
        )
        repair_intent = (
            technical_context.get("repair_intent")
            if isinstance(technical_context.get("repair_intent"), dict)
            else {}
        )
        affected_symbols = [patch_candidate.target_symbol] if patch_candidate.target_symbol else []
        affected_modules = [Path(patch_candidate.target_file).parent.as_posix() or patch_candidate.target_file] if patch_candidate.target_file else []
        behavior_summary = str(
            transformation.get("behavior_summary")
            or repair_task.get("behavior_to_create")
            or patch_candidate.semantic_goal
            or ""
        ).strip()
        strategy = str(
            transformation.get("transformation_strategy")
            or patch_candidate.replacement_strategy
            or ""
        ).strip()
        constraints = [
            str(item).strip()
            for item in list(transformation.get("constraints") or repair_task.get("repair_boundary") or patch_candidate.optional_constraints)
            if str(item).strip()
        ]
        invariants = [
            str(item).strip()
            for item in list(transformation.get("invariants") or repair_task.get("invariants") or repair_task.get("repair_boundary") or [])
            if str(item).strip()
        ]
        success_criteria = [
            str(item).strip()
            for item in list(transformation.get("success_criteria") or repair_task.get("postconditions") or [])
            if str(item).strip()
        ]
        success_condition = str(
            repair_task.get("success_condition")
            or repair_intent.get("success_condition")
            or ""
        ).strip()
        if success_condition:
            success_criteria.append(success_condition)

        compatibility = "; ".join(list(dict.fromkeys(invariants or constraints)))
        if not compatibility:
            compatibility = "Preserve existing public contracts and keep the change scoped to the selected edit unit."

        rollback_side_effects = [
            str(item).strip()
            for item in list(repair_task.get("invariants") or [])
            if str(item).strip()
        ]
        confidence_label = self._confidence_label(patch_candidate.confidence)

        proposal = RepairProposalArtifact(
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
            intent=behavior_summary or patch_candidate.semantic_goal or "",
            concrete_change=RepairProposalConcreteChange(
                objective=behavior_summary or patch_candidate.semantic_goal or "",
                current_behavior=patch_candidate.observed_behavior,
                expected_behavior=patch_candidate.expected_behavior,
                behavior_summary=behavior_summary or patch_candidate.expected_behavior,
                modification_strategy=strategy,
                affected_symbols=affected_symbols,
                constraints=list(dict.fromkeys(constraints)),
                invariants=list(dict.fromkeys(invariants)),
                success_criteria=list(dict.fromkeys(success_criteria)),
                reasoning="",
                suggested_replacement="",
            ),
            rollback=RepairProposalRollback(
                possible=bool(patch_candidate.target_file and patch_candidate.target_symbol),
                strategy=(
                    "Restore the previous logic in the selected edit unit if validation or regression checks fail."
                    if patch_candidate.target_file and patch_candidate.target_symbol
                    else ""
                ),
                affected_symbols=list(affected_symbols),
                side_effects=list(dict.fromkeys(rollback_side_effects)),
            ),
            impact=RepairProposalImpact(
                scope="focused_edit_unit" if patch_candidate.symbol_kind != "file" else "file_edit_unit",
                affected_modules=affected_modules,
                runtime_behavior=patch_candidate.expected_behavior or patch_candidate.semantic_goal,
                compatibility=compatibility,
                risk_level=patch_candidate.risk_level or "medium",
            ),
            risks=RepairProposalRisks(
                technical=(
                    ["The selected edit unit may depend on neighboring logic outside the current snippet."]
                    if patch_candidate.current_content_excerpt
                    else []
                ),
                behavioral=(
                    [success_condition]
                    if success_condition
                    else ([patch_candidate.expected_behavior] if patch_candidate.expected_behavior else [])
                ),
                regression=(
                    ["Validate the observed failing path and a known-good path before promotion."]
                    if patch_candidate.evidence_refs
                    else []
                ),
                confidence=confidence_label,
            ),
            confidence=patch_candidate.confidence,
            evidence_refs=list(patch_candidate.evidence_refs),
            diagnostics=[
                "repair_proposal:compiled_from_patch_candidate",
                *[f"success_criteria:{item}" for item in list(dict.fromkeys(success_criteria))],
            ],
            warnings=[],
            field_origins={
                "target": ["technical_localization"],
                "intent": ["repair_task", "candidate_transformation"],
                "concrete_change": ["repair_task", "candidate_transformation", "patch_candidate"],
                "rollback": ["repair_task", "patch_candidate"],
                "impact": ["repair_task", "patch_candidate"],
                "risks": ["patch_candidate", "candidate_transformation", "evidence_refs"],
            },
            assembly=self._proposal_assembly(patch_candidate),
        )
        return proposal

    def merge(
        self,
        proposal: RepairProposalArtifact,
        patch_candidate: PatchCandidateArtifact,
    ) -> RepairProposalArtifact:
        scaffold = self.compile(patch_candidate)
        merged = proposal.model_copy(
            update={
                "diagnosis_id": proposal.diagnosis_id or scaffold.diagnosis_id,
                "candidate_id": proposal.candidate_id or scaffold.candidate_id,
                "task_run_id": proposal.task_run_id or scaffold.task_run_id,
                "execution_plan_id": proposal.execution_plan_id or scaffold.execution_plan_id,
                "target": RepairProposalTarget(
                    workspace=proposal.target.workspace or scaffold.target.workspace,
                    file=proposal.target.file or scaffold.target.file,
                    symbol=proposal.target.symbol or scaffold.target.symbol,
                    symbol_kind=proposal.target.symbol_kind or scaffold.target.symbol_kind,
                ),
                "intent": proposal.intent or scaffold.intent,
                "concrete_change": RepairProposalConcreteChange(
                    objective=proposal.concrete_change.objective or scaffold.concrete_change.objective,
                    current_behavior=proposal.concrete_change.current_behavior or scaffold.concrete_change.current_behavior,
                    expected_behavior=proposal.concrete_change.expected_behavior or scaffold.concrete_change.expected_behavior,
                    behavior_summary=proposal.concrete_change.behavior_summary or scaffold.concrete_change.behavior_summary,
                    modification_strategy=proposal.concrete_change.modification_strategy or scaffold.concrete_change.modification_strategy,
                    affected_symbols=proposal.concrete_change.affected_symbols or scaffold.concrete_change.affected_symbols,
                    constraints=proposal.concrete_change.constraints or scaffold.concrete_change.constraints,
                    invariants=proposal.concrete_change.invariants or scaffold.concrete_change.invariants,
                    success_criteria=proposal.concrete_change.success_criteria or scaffold.concrete_change.success_criteria,
                    reasoning=proposal.concrete_change.reasoning,
                    suggested_replacement=proposal.concrete_change.suggested_replacement,
                ),
                "rollback": RepairProposalRollback(
                    possible=proposal.rollback.possible or scaffold.rollback.possible,
                    strategy=proposal.rollback.strategy or scaffold.rollback.strategy,
                    affected_symbols=proposal.rollback.affected_symbols or scaffold.rollback.affected_symbols,
                    side_effects=proposal.rollback.side_effects or scaffold.rollback.side_effects,
                ),
                "impact": RepairProposalImpact(
                    scope=proposal.impact.scope or scaffold.impact.scope,
                    affected_modules=proposal.impact.affected_modules or scaffold.impact.affected_modules,
                    runtime_behavior=proposal.impact.runtime_behavior or scaffold.impact.runtime_behavior,
                    compatibility=proposal.impact.compatibility or scaffold.impact.compatibility,
                    risk_level=proposal.impact.risk_level or scaffold.impact.risk_level,
                ),
                "risks": RepairProposalRisks(
                    technical=proposal.risks.technical or scaffold.risks.technical,
                    behavioral=proposal.risks.behavioral or scaffold.risks.behavioral,
                    regression=proposal.risks.regression or scaffold.risks.regression,
                    confidence=proposal.risks.confidence or scaffold.risks.confidence,
                ),
                "confidence": proposal.confidence or scaffold.confidence,
                "evidence_refs": list(dict.fromkeys([*proposal.evidence_refs, *scaffold.evidence_refs])),
                "diagnostics": list(dict.fromkeys([*scaffold.diagnostics, *proposal.diagnostics])),
                "warnings": list(dict.fromkeys([*scaffold.warnings, *proposal.warnings])),
                "field_origins": self._merge_field_origins(proposal.field_origins, scaffold.field_origins),
                "assembly": self._merge_proposal_assembly(proposal.assembly, scaffold.assembly),
            }
        )
        return merged

    def partial(
        self,
        patch_candidate: PatchCandidateArtifact,
        *,
        warning: str,
    ) -> RepairProposalArtifact:
        proposal = self.compile(patch_candidate)
        diagnostics = list(proposal.diagnostics)
        diagnostics.append("repair_proposal:incomplete")
        if not patch_candidate.target_file or not patch_candidate.target_symbol:
            diagnostics.append("target:incomplete")
        if not patch_candidate.expected_behavior or not patch_candidate.observed_behavior:
            diagnostics.append("behavior:missing_fields")
        if not patch_candidate.replacement_strategy:
            diagnostics.append("strategy:missing_fields")
        return proposal.model_copy(
            update={
                "warnings": list(dict.fromkeys([warning, "repair_proposal_partial_from_patch_candidate"])),
                "diagnostics": list(dict.fromkeys(diagnostics)),
            }
        )

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

    def _proposal_assembly_stage(self, payload: object) -> RepairProposalAssemblyStage:
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
        return proposal.model_copy(
            update={
                "artifact_id": proposal.artifact_id or scaffold.artifact_id,
                "status": proposal.status if proposal.status != "missing" else scaffold.status,
                "coverage_score": proposal.coverage_score or scaffold.coverage_score,
                "confidence": proposal.confidence or scaffold.confidence,
                "reason_codes": list(dict.fromkeys([*scaffold.reason_codes, *proposal.reason_codes])),
                "diagnostics": list(dict.fromkeys([*scaffold.diagnostics, *proposal.diagnostics])),
            }
        )

    def _merge_field_origins(
        self,
        proposal: dict[str, list[str]],
        scaffold: dict[str, list[str]],
    ) -> dict[str, list[str]]:
        merged: dict[str, list[str]] = {}
        for key in set(scaffold) | set(proposal):
            merged[key] = list(
                dict.fromkeys(
                    [
                        *[str(item).strip() for item in list(scaffold.get(key) or []) if str(item).strip()],
                        *[str(item).strip() for item in list(proposal.get(key) or []) if str(item).strip()],
                    ]
                )
            )
        return merged

    def _confidence_label(self, value: float) -> str:
        if value >= 0.8:
            return "alta"
        if value >= 0.55:
            return "media"
        return "baixa"
