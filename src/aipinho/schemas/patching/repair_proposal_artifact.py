from __future__ import annotations

from typing import Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


RepairProposalComponentStatus = Literal["complete", "partial", "missing", "invalid"]


class RepairProposalComponent(AIpinhoModel):
    status: RepairProposalComponentStatus = "missing"
    content: dict[str, object] = Field(default_factory=dict)
    reason_codes: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    diagnostics: list[str] = Field(default_factory=list)

    @property
    def available(self) -> bool:
        return self.status in {"complete", "partial"}


class RepairProposalComponents(AIpinhoModel):
    target: RepairProposalComponent = Field(default_factory=RepairProposalComponent)
    behavior: RepairProposalComponent = Field(default_factory=RepairProposalComponent)
    strategy: RepairProposalComponent = Field(default_factory=RepairProposalComponent)
    impact: RepairProposalComponent = Field(default_factory=RepairProposalComponent)
    rollback: RepairProposalComponent = Field(default_factory=RepairProposalComponent)
    confidence: RepairProposalComponent = Field(default_factory=RepairProposalComponent)


class RepairProposalTarget(AIpinhoModel):
    workspace: str = ""
    file: str = ""
    symbol: str = ""
    symbol_kind: str = "file"


class RepairProposalConcreteChange(AIpinhoModel):
    objective: str = ""
    current_behavior: str = ""
    expected_behavior: str = ""
    behavior_summary: str = ""
    modification_strategy: str = ""
    affected_symbols: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    invariants: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    reasoning: str = ""
    suggested_replacement: str = ""


class RepairProposalRollback(AIpinhoModel):
    possible: bool = False
    strategy: str = ""
    affected_symbols: list[str] = Field(default_factory=list)
    side_effects: list[str] = Field(default_factory=list)


class RepairProposalImpact(AIpinhoModel):
    scope: str = ""
    affected_modules: list[str] = Field(default_factory=list)
    runtime_behavior: str = ""
    compatibility: str = ""
    risk_level: str = ""


class RepairProposalRisks(AIpinhoModel):
    technical: list[str] = Field(default_factory=list)
    behavioral: list[str] = Field(default_factory=list)
    regression: list[str] = Field(default_factory=list)
    confidence: str = ""


class RepairProposalAssemblyStage(AIpinhoModel):
    artifact_id: str = ""
    status: RepairProposalComponentStatus = "missing"
    coverage_score: int = 0
    confidence: float = 0.0
    reason_codes: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)


class RepairProposalAssembly(AIpinhoModel):
    semantic_evidence: RepairProposalAssemblyStage = Field(default_factory=RepairProposalAssemblyStage)
    behavior_localization: RepairProposalAssemblyStage = Field(default_factory=RepairProposalAssemblyStage)
    behavior_justification: RepairProposalAssemblyStage = Field(default_factory=RepairProposalAssemblyStage)
    candidate_transformation: RepairProposalAssemblyStage = Field(default_factory=RepairProposalAssemblyStage)

    @property
    def assembly_score(self) -> float:
        scores = [
            max(0.0, min(1.0, stage.coverage_score / 100.0))
            for stage in (
                self.semantic_evidence,
                self.behavior_localization,
                self.behavior_justification,
                self.candidate_transformation,
            )
        ]
        return round(sum(scores) / max(len(scores), 1), 3)

    @property
    def assembly_status(self) -> RepairProposalComponentStatus:
        stages = (
            self.semantic_evidence,
            self.behavior_localization,
            self.behavior_justification,
            self.candidate_transformation,
        )
        if all(stage.status == "complete" for stage in stages):
            return "complete"
        if any(stage.status in {"complete", "partial"} for stage in stages):
            return "partial"
        return "missing"


class RepairProposalArtifact(AIpinhoModel):
    proposal_id: str = Field(default_factory=lambda: f"repair_proposal_{uuid4().hex}")
    diagnosis_id: str = ""
    candidate_id: str = ""
    task_run_id: str | None = None
    execution_plan_id: str | None = None
    proposal_status: RepairProposalComponentStatus = "missing"
    proposal_completeness: float = 0.0
    target: RepairProposalTarget = Field(default_factory=RepairProposalTarget)
    intent: str = ""
    concrete_change: RepairProposalConcreteChange = Field(default_factory=RepairProposalConcreteChange)
    rollback: RepairProposalRollback = Field(default_factory=RepairProposalRollback)
    impact: RepairProposalImpact = Field(default_factory=RepairProposalImpact)
    risks: RepairProposalRisks = Field(default_factory=RepairProposalRisks)
    confidence: float = 0.0
    evidence_refs: list[str] = Field(default_factory=list)
    field_origins: dict[str, list[str]] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    diagnostics: list[str] = Field(default_factory=list)
    components: RepairProposalComponents = Field(default_factory=RepairProposalComponents)
    assembly: RepairProposalAssembly = Field(default_factory=RepairProposalAssembly)

    def __init__(self, **data):
        super().__init__(**data)
        self._refresh_components()

    def supports_preview(self) -> bool:
        self._refresh_components()
        return all(
            component.status == "complete"
            for component in [
                self.components.target,
                self.components.behavior,
                self.components.strategy,
                self.components.impact,
                self.components.rollback,
                self.components.confidence,
            ]
        )

    def compiler_replacement(self) -> str:
        return str(self.concrete_change.suggested_replacement or "").strip()

    def model_dump(self, *args, **kwargs):
        self._refresh_components()
        return super().model_dump(*args, **kwargs)

    def missing_reason_codes(self) -> list[str]:
        self._refresh_components()
        reason_codes: list[str] = []
        for component in [
            self.components.target,
            self.components.behavior,
            self.components.strategy,
            self.components.impact,
            self.components.rollback,
            self.components.confidence,
        ]:
            if component.status != "complete":
                reason_codes.extend(component.reason_codes)
        return self._dedupe(reason_codes)

    def _refresh_components(self) -> None:
        components = RepairProposalComponents(
            target=self._target_component(),
            behavior=self._behavior_component(),
            strategy=self._strategy_component(),
            impact=self._impact_component(),
            rollback=self._rollback_component(),
            confidence=self._confidence_component(),
        )
        self.components = components
        component_list = [
            components.target,
            components.behavior,
            components.strategy,
            components.impact,
            components.rollback,
            components.confidence,
        ]
        component_scores = [self._component_score(item) for item in component_list]
        self.proposal_completeness = round(sum(component_scores) / max(len(component_scores), 1), 3)
        available = [item for item in component_list if item.available]
        if all(item.status == "complete" for item in component_list):
            self.proposal_status = "complete"
        elif available:
            self.proposal_status = "partial"
        else:
            self.proposal_status = "missing"
        self.diagnostics = self._dedupe(
            [
                *self.diagnostics,
                *[diagnostic for item in component_list for diagnostic in item.diagnostics],
            ]
        )

    def _target_component(self) -> RepairProposalComponent:
        content = {
            "workspace": self.target.workspace,
            "file": self.target.file,
            "symbol": self.target.symbol,
            "symbol_kind": self.target.symbol_kind,
            "intent": self.intent,
        }
        present = [name for name, value in content.items() if self._has_value(value)]
        reason_codes: list[str] = []
        diagnostics: list[str] = []
        if not self.target.file.strip():
            reason_codes.append("PROPOSAL_TARGET_MISSING")
            diagnostics.append("target:incomplete")
        if not self.target.symbol.strip():
            reason_codes.append("PROPOSAL_SYMBOLS_MISSING")
            diagnostics.append("target:incomplete")
        if not self.intent.strip():
            reason_codes.append("PROPOSAL_TARGET_MISSING")
            diagnostics.append("target:incomplete")
        status = self._status_from_fields(present_count=len(present), total=5, reason_codes=reason_codes)
        return RepairProposalComponent(
            status=status,
            content=content,
            reason_codes=self._dedupe(reason_codes),
            confidence=self.confidence,
            diagnostics=diagnostics,
        )

    def _behavior_component(self) -> RepairProposalComponent:
        content = {
            "objective": self.concrete_change.objective,
            "current_behavior": self.concrete_change.current_behavior,
            "expected_behavior": self.concrete_change.expected_behavior,
            "behavior_summary": self.concrete_change.behavior_summary,
            "success_criteria": list(self.concrete_change.success_criteria),
        }
        present = [name for name, value in content.items() if self._has_value(value)]
        reason_codes: list[str] = []
        diagnostics: list[str] = []
        if len(present) < len(content):
            reason_codes.extend(["PROPOSAL_BEHAVIOR_MISSING", "PROPOSAL_CONCRETE_CHANGE_MISSING"])
            diagnostics.append("behavior:missing_fields")
        status = self._status_from_fields(present_count=len(present), total=len(content), reason_codes=reason_codes)
        return RepairProposalComponent(
            status=status,
            content=content,
            reason_codes=self._dedupe(reason_codes),
            confidence=self.confidence,
            diagnostics=diagnostics,
        )

    def _strategy_component(self) -> RepairProposalComponent:
        content = {
            "modification_strategy": self.concrete_change.modification_strategy,
            "affected_symbols": list(self.concrete_change.affected_symbols),
            "constraints": list(self.concrete_change.constraints),
            "invariants": list(self.concrete_change.invariants),
            "reasoning": self.concrete_change.reasoning,
        }
        present = [name for name, value in content.items() if self._has_value(value)]
        reason_codes: list[str] = []
        diagnostics: list[str] = []
        if len(present) < len(content):
            reason_codes.extend(["PROPOSAL_STRATEGY_MISSING", "PROPOSAL_CONCRETE_CHANGE_MISSING"])
            diagnostics.append("strategy:missing_fields")
        status = self._status_from_fields(present_count=len(present), total=len(content), reason_codes=reason_codes)
        return RepairProposalComponent(
            status=status,
            content=content,
            reason_codes=self._dedupe(reason_codes),
            confidence=self.confidence,
            diagnostics=diagnostics,
        )

    def _impact_component(self) -> RepairProposalComponent:
        content = {
            "scope": self.impact.scope,
            "affected_modules": list(self.impact.affected_modules),
            "runtime_behavior": self.impact.runtime_behavior,
            "compatibility": self.impact.compatibility,
            "risk_level": self.impact.risk_level,
        }
        present = [name for name, value in content.items() if self._has_value(value)]
        reason_codes: list[str] = []
        diagnostics: list[str] = []
        if len(present) < len(content):
            reason_codes.append("PROPOSAL_IMPACT_MISSING")
            diagnostics.append("impact:missing_fields")
        status = self._status_from_fields(present_count=len(present), total=len(content), reason_codes=reason_codes)
        return RepairProposalComponent(
            status=status,
            content=content,
            reason_codes=self._dedupe(reason_codes),
            confidence=self.confidence,
            diagnostics=diagnostics,
        )

    def _rollback_component(self) -> RepairProposalComponent:
        content = {
            "possible": self.rollback.possible,
            "strategy": self.rollback.strategy,
            "affected_symbols": list(self.rollback.affected_symbols),
            "side_effects": list(self.rollback.side_effects),
        }
        present = [name for name, value in content.items() if self._has_value(value)]
        reason_codes: list[str] = []
        diagnostics: list[str] = []
        if len(present) < len(content):
            reason_codes.append("PROPOSAL_ROLLBACK_MISSING")
            diagnostics.append("rollback:missing_fields")
        status = self._status_from_fields(present_count=len(present), total=len(content), reason_codes=reason_codes)
        return RepairProposalComponent(
            status=status,
            content=content,
            reason_codes=self._dedupe(reason_codes),
            confidence=self.confidence,
            diagnostics=diagnostics,
        )

    def _confidence_component(self) -> RepairProposalComponent:
        content = {
            "confidence": self.confidence,
            "technical": list(self.risks.technical),
            "behavioral": list(self.risks.behavioral),
            "regression": list(self.risks.regression),
            "confidence_label": self.risks.confidence,
        }
        present = ["confidence"]
        present.extend(
            name
            for name, value in content.items()
            if name != "confidence" and self._has_value(value)
        )
        reason_codes: list[str] = []
        diagnostics: list[str] = []
        if not (
            self.risks.technical
            or self.risks.behavioral
            or self.risks.regression
            or self.risks.confidence.strip()
        ):
            reason_codes.extend(["PROPOSAL_RISK_MISSING", "PROPOSAL_CONFIDENCE_MISSING"])
            diagnostics.append("confidence:missing_fields")
        status = self._status_from_fields(present_count=len(present), total=len(content), reason_codes=reason_codes)
        return RepairProposalComponent(
            status=status,
            content=content,
            reason_codes=self._dedupe(reason_codes),
            confidence=self.confidence,
            diagnostics=diagnostics,
        )

    def _status_from_fields(
        self,
        *,
        present_count: int,
        total: int,
        reason_codes: list[str],
    ) -> RepairProposalComponentStatus:
        if present_count <= 0:
            return "missing"
        if reason_codes:
            return "partial"
        if present_count >= total:
            return "complete"
        return "partial"

    def _component_score(self, component: RepairProposalComponent) -> float:
        if component.status == "complete":
            return 1.0
        if component.status == "partial":
            return 0.5
        return 0.0

    def _has_value(self, value: object) -> bool:
        if isinstance(value, bool):
            return True
        if isinstance(value, (int, float)):
            return value > 0
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, set, dict)):
            return bool(value)
        return value is not None

    def _dedupe(self, values: list[str]) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for value in values:
            text = str(value or "").strip()
            if not text or text in seen:
                continue
            seen.add(text)
            ordered.append(text)
        return ordered
