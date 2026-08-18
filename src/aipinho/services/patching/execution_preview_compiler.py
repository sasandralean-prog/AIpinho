from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.schemas.patching.execution_intent_artifact import (
    ExecutableChangeUnit,
    ExecutablePlanArtifact,
    ExecutionIntentArtifact,
    ExecutionPreviewArtifact,
)
from aipinho.schemas.patching.repair_proposal_artifact import RepairProposalArtifact


class ExecutionPreviewCompiler:
    """Compiles governed execution IRs from a repair proposal and canonical patch plan.

    This compiler is deterministic. It does not execute patches, create approvals,
    or decide policy. Its only job is to reduce the semantic jump between
    RepairProposal and ApprovalRequest by producing auditable operational
    representations.
    """

    def compile(
        self,
        *,
        repair_proposal: RepairProposalArtifact | dict[str, Any] | None,
        patch_plan: dict[str, Any] | None,
        workspace_hint: str | None = None,
    ) -> tuple[ExecutionIntentArtifact, ExecutablePlanArtifact, ExecutionPreviewArtifact]:
        proposal = self._proposal(repair_proposal)
        plan = dict(patch_plan or {})
        workspace = str(proposal.target.workspace or plan.get("workspace") or workspace_hint or "").strip()
        target_files = self._resolved_target_files(plan, workspace=workspace)
        target_symbols = list(dict.fromkeys([proposal.target.symbol] if proposal.target.symbol else []))

        intent = ExecutionIntentArtifact(
            proposal_id=proposal.proposal_id,
            patch_plan_id=str(plan.get("patch_plan_id") or plan.get("plan_id") or ""),
            workspace=workspace,
            semantic_goal=str(proposal.intent or proposal.concrete_change.objective or "").strip(),
            operation_kind="patch_request",
            target_files=target_files,
            target_symbols=target_symbols,
            preconditions=self._preconditions(proposal, target_files),
            postconditions=self._postconditions(proposal),
            constraints=list(dict.fromkeys(str(item).strip() for item in proposal.concrete_change.constraints if str(item).strip())),
            invariants=list(dict.fromkeys(str(item).strip() for item in proposal.concrete_change.invariants if str(item).strip())),
            risk_level=str(proposal.impact.risk_level or proposal.risks.confidence or "").strip(),
            confidence=float(proposal.confidence or 0.0),
            evidence_refs=list(dict.fromkeys(proposal.evidence_refs)),
            diagnostics=[],
        )
        intent.status, intent.completeness, intent.diagnostics = self._intent_state(intent, proposal)

        executable = ExecutablePlanArtifact(
            execution_intent_id=intent.intent_id,
            patch_plan_id=intent.patch_plan_id,
            workspace=workspace,
            target_paths=target_files,
            operations=["apply_patch_after_approval"] if target_files else [],
            change_units=self._change_units(plan, proposal, target_files),
            validation_steps=self._validation_steps(plan, proposal),
            rollback_strategy=self._rollback_strategy(proposal, plan),
            checkpoints=self._checkpoints(plan, proposal),
            evidence_refs=list(dict.fromkeys([*intent.evidence_refs, f"repair_proposal:{proposal.proposal_id}" if proposal.proposal_id else ""])),
            diagnostics=[],
        )
        executable.evidence_refs = [item for item in executable.evidence_refs if item]
        executable.status, executable.completeness, executable.diagnostics = self._executable_state(executable, proposal)

        preview = ExecutionPreviewArtifact(
            executable_plan_id=executable.executable_plan_id,
            execution_intent_id=intent.intent_id,
            patch_plan_id=intent.patch_plan_id,
            operation_kind="patch_request",
            target_paths=list(executable.target_paths),
            operations=list(executable.operations),
            change_summary=self._change_summary(executable, proposal),
            risk_summary=self._risk_summary(proposal),
            rollback_summary=self._rollback_summary(proposal),
            impact_summary=self._impact_summary(proposal),
            dependency_summary=self._dependency_summary(executable),
            validation_summary=list(executable.validation_steps),
            evidence_refs=list(dict.fromkeys([*executable.evidence_refs, f"patch_plan:{intent.patch_plan_id}" if intent.patch_plan_id else ""])),
            diagnostics=[],
        )
        preview.evidence_refs = [item for item in preview.evidence_refs if item]
        preview.status, preview.completeness, preview.diagnostics = self._preview_state(preview, proposal, executable)
        return intent, executable, preview

    def _proposal(self, value: RepairProposalArtifact | dict[str, Any] | None) -> RepairProposalArtifact:
        if isinstance(value, RepairProposalArtifact):
            return value
        if isinstance(value, dict):
            return RepairProposalArtifact(**value)
        return RepairProposalArtifact()

    def _resolved_target_files(self, plan: dict[str, Any], *, workspace: str) -> list[str]:
        values: list[str] = []
        for item in list(plan.get("files_to_modify") or []) + list(plan.get("patch_operations") or []) + list(plan.get("affected_files") or []):
            if not isinstance(item, dict):
                continue
            raw = item.get("path") or item.get("target_path") or item.get("normalized_path") or item.get("relative_path") or item.get("file_path")
            resolved = self._resolve_path(raw, workspace=workspace)
            if resolved and resolved not in values:
                values.append(resolved)
        return values

    def _resolve_path(self, raw: Any, *, workspace: str) -> str:
        text = str(raw or "").strip()
        if not text:
            return ""
        try:
            path = Path(text)
        except (OSError, ValueError):
            return ""
        if path.is_absolute():
            return str(path.resolve(strict=False))
        if workspace:
            return str((Path(workspace) / path).resolve(strict=False))
        return text

    def _preconditions(self, proposal: RepairProposalArtifact, target_files: list[str]) -> list[str]:
        values = []
        if proposal.proposal_status in {"complete", "partial"}:
            values.append("repair_proposal_available")
        if target_files:
            values.append("target_files_resolved")
        if proposal.target.symbol:
            values.append("target_symbol_resolved")
        if proposal.concrete_change.expected_behavior:
            values.append("expected_behavior_defined")
        return values

    def _postconditions(self, proposal: RepairProposalArtifact) -> list[str]:
        values = list(proposal.concrete_change.success_criteria)
        if proposal.concrete_change.expected_behavior:
            values.append(proposal.concrete_change.expected_behavior)
        return list(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))

    def _change_units(
        self,
        plan: dict[str, Any],
        proposal: RepairProposalArtifact,
        target_files: list[str],
    ) -> list[ExecutableChangeUnit]:
        hunk_map: dict[str, list[dict[str, Any]]] = {}
        for hunk in plan.get("hunks", []) or []:
            if not isinstance(hunk, dict):
                continue
            key = str(hunk.get("file_path") or "").replace("\\", "/").strip("/")
            hunk_map.setdefault(key, []).append(hunk)
        units: list[ExecutableChangeUnit] = []
        for index, target in enumerate(target_files):
            relative_key = self._relative_key(target, workspace=str(plan.get("workspace") or proposal.target.workspace or ""))
            hunks = hunk_map.get(relative_key, [])
            units.append(
                ExecutableChangeUnit(
                    target_file=target,
                    target_symbol=proposal.target.symbol,
                    operation="apply_patch_after_approval",
                    order_index=index,
                    checkpoints=self._checkpoints(plan, proposal),
                    validation_requirements=self._validation_steps(plan, proposal),
                    rollback_strategy=str(proposal.rollback.strategy or "").strip(),
                    hunk_ids=[str(item.get("hunk_id") or "") for item in hunks if str(item.get("hunk_id") or "").strip()],
                    evidence_refs=list(dict.fromkeys([*proposal.evidence_refs, *[f"hunk:{item.get('hunk_id')}" for item in hunks if item.get('hunk_id')]])),
                    diagnostics=["change_unit:missing_hunks"] if not hunks else [],
                    confidence=float(proposal.confidence or 0.0),
                )
            )
        return units

    def _relative_key(self, target: str, *, workspace: str) -> str:
        path = Path(target)
        if workspace:
            try:
                return str(path.resolve(strict=False).relative_to(Path(workspace).resolve(strict=False))).replace("\\", "/").strip("/")
            except Exception:
                pass
        return path.name.replace("\\", "/").strip("/")

    def _validation_steps(self, plan: dict[str, Any], proposal: RepairProposalArtifact) -> list[str]:
        values = []
        validation = plan.get("validation") if isinstance(plan.get("validation"), dict) else {}
        for key in ("status", "summary"):
            if validation.get(key):
                values.append(str(validation.get(key)))
        values.extend(str(item).strip() for item in proposal.concrete_change.success_criteria if str(item).strip())
        values.append("validation_result_required")
        return list(dict.fromkeys(values))

    def _rollback_strategy(self, proposal: RepairProposalArtifact, plan: dict[str, Any]) -> dict[str, object]:
        notes = []
        for item in plan.get("rollback_notes", []) or []:
            if isinstance(item, dict):
                value = item.get("note") or item.get("summary") or item.get("strategy")
                if value:
                    notes.append(str(value))
        return {
            "possible": bool(proposal.rollback.possible),
            "strategy": str(proposal.rollback.strategy or "").strip(),
            "notes": notes,
        }

    def _checkpoints(self, plan: dict[str, Any], proposal: RepairProposalArtifact) -> list[str]:
        values = ["ExecutionPlanCreated", "ExecutionPlanApproved", "ExecutionStarted", "ValidationFinished"]
        if proposal.rollback.strategy:
            values.append("RollbackAvailable")
        if plan.get("diff_ref"):
            values.append("DiffReferenceBound")
        return values

    def _change_summary(self, executable: ExecutablePlanArtifact, proposal: RepairProposalArtifact) -> list[str]:
        values = []
        if proposal.concrete_change.modification_strategy:
            values.append(proposal.concrete_change.modification_strategy)
        for unit in executable.change_units:
            if unit.target_file:
                values.append(f"{unit.operation}:{unit.target_file}")
        return list(dict.fromkeys(values))

    def _risk_summary(self, proposal: RepairProposalArtifact) -> list[str]:
        values = [
            *proposal.risks.technical,
            *proposal.risks.behavioral,
            *proposal.risks.regression,
        ]
        if proposal.impact.risk_level:
            values.append(f"risk_level:{proposal.impact.risk_level}")
        return list(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))

    def _rollback_summary(self, proposal: RepairProposalArtifact) -> list[str]:
        values = []
        if proposal.rollback.strategy:
            values.append(proposal.rollback.strategy)
        values.extend(str(item).strip() for item in proposal.rollback.side_effects if str(item).strip())
        return list(dict.fromkeys(values))

    def _impact_summary(self, proposal: RepairProposalArtifact) -> list[str]:
        values = []
        for value in (
            proposal.impact.scope,
            proposal.impact.runtime_behavior,
            proposal.impact.compatibility,
        ):
            if str(value).strip():
                values.append(str(value).strip())
        values.extend(str(item).strip() for item in proposal.impact.affected_modules if str(item).strip())
        return list(dict.fromkeys(values))

    def _dependency_summary(self, executable: ExecutablePlanArtifact) -> list[str]:
        values = []
        if executable.change_units:
            values.append("change_units_available")
        if executable.rollback_strategy.get("strategy"):
            values.append("rollback_strategy_available")
        if executable.validation_steps:
            values.append("validation_plan_available")
        return values

    def _intent_state(
        self,
        intent: ExecutionIntentArtifact,
        proposal: RepairProposalArtifact,
    ) -> tuple[str, float, list[str]]:
        score = 0
        diagnostics: list[str] = []
        if intent.semantic_goal:
            score += 1
        else:
            diagnostics.append("EXECUTION_INTENT_GOAL_MISSING")
        if intent.target_files:
            score += 1
        else:
            diagnostics.append("EXECUTION_INTENT_TARGET_FILES_MISSING")
        if intent.target_symbols:
            score += 1
        else:
            diagnostics.append("EXECUTION_INTENT_TARGET_SYMBOLS_MISSING")
        if intent.postconditions:
            score += 1
        else:
            diagnostics.append("EXECUTION_INTENT_POSTCONDITIONS_MISSING")
        if proposal.components.behavior.status == "complete":
            score += 1
        else:
            diagnostics.append("EXECUTION_INTENT_BEHAVIOR_INCOMPLETE")
        completeness = round(score / 5.0, 3)
        if score == 5:
            return "complete", completeness, diagnostics
        if score > 0:
            return "partial", completeness, diagnostics
        return "missing", completeness, diagnostics

    def _executable_state(
        self,
        executable: ExecutablePlanArtifact,
        proposal: RepairProposalArtifact,
    ) -> tuple[str, float, list[str]]:
        score = 0
        diagnostics: list[str] = []
        if executable.target_paths:
            score += 1
        else:
            diagnostics.append("EXECUTABLE_PLAN_TARGET_PATHS_MISSING")
        if executable.change_units:
            score += 1
        else:
            diagnostics.append("EXECUTABLE_PLAN_CHANGE_UNITS_MISSING")
        if all(unit.hunk_ids for unit in executable.change_units):
            score += 1
        else:
            diagnostics.append("EXECUTABLE_PLAN_HUNKS_MISSING")
        if executable.rollback_strategy.get("strategy"):
            score += 1
        else:
            diagnostics.append("EXECUTABLE_PLAN_ROLLBACK_MISSING")
        if proposal.components.strategy.status == "complete":
            score += 1
        else:
            diagnostics.append("EXECUTABLE_PLAN_STRATEGY_INCOMPLETE")
        completeness = round(score / 5.0, 3)
        if score == 5:
            return "complete", completeness, diagnostics
        if score > 0:
            return "partial", completeness, diagnostics
        return "missing", completeness, diagnostics

    def _preview_state(
        self,
        preview: ExecutionPreviewArtifact,
        proposal: RepairProposalArtifact,
        executable: ExecutablePlanArtifact,
    ) -> tuple[str, float, list[str]]:
        score = 0
        diagnostics: list[str] = []
        if executable.status == "complete":
            score += 1
        else:
            diagnostics.append("EXECUTION_PREVIEW_EXECUTABLE_PLAN_INCOMPLETE")
        if preview.target_paths:
            score += 1
        else:
            diagnostics.append("EXECUTION_PREVIEW_TARGET_PATHS_MISSING")
        if preview.change_summary:
            score += 1
        else:
            diagnostics.append("EXECUTION_PREVIEW_CHANGE_SUMMARY_MISSING")
        if proposal.components.impact.status == "complete":
            score += 1
        else:
            diagnostics.append("EXECUTION_PREVIEW_IMPACT_INCOMPLETE")
        if proposal.components.rollback.status == "complete":
            score += 1
        else:
            diagnostics.append("EXECUTION_PREVIEW_ROLLBACK_INCOMPLETE")
        completeness = round(score / 5.0, 3)
        if score == 5:
            return "complete", completeness, diagnostics
        if score > 0:
            return "partial", completeness, diagnostics
        return "missing", completeness, diagnostics
