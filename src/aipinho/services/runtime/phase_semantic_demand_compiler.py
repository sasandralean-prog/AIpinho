from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from aipinho.schemas.runtime.phase_dependency_evaluation import (
    DownstreamPhaseRequirements,
    PhaseSemanticDemandCompilation,
    RequirementProvenance,
)
from aipinho.services.runtime.phase_dependency_contract_registry import PhaseDependencyContractRegistry


class PhaseSemanticDemandCompiler:
    """Compiles downstream dependency requirements from the canonical plan."""

    _LIMITATION_STRENGTH = {
        "NOT_APPLICABLE": 0,
        "COMPATIBLE": 1,
        "COMPATIBLE_WITH_CONSTRAINT": 2,
        "UNKNOWN": 3,
        "INCOMPATIBLE": 4,
    }

    def __init__(self, *, system_invariants: PhaseDependencyContractRegistry | None = None) -> None:
        self.system_invariants = system_invariants or PhaseDependencyContractRegistry()

    def compile_for_run(
        self,
        *,
        run: Any,
        consumer_phase_id: str,
        consumer_operation_type: str | None = None,
        source_step_id: str | None = None,
    ) -> PhaseSemanticDemandCompilation:
        plan = getattr(run, "plan", None)
        canonical = getattr(plan, "canonical_execution_plan", None)
        plan_id = str(getattr(plan, "plan_id", "") or "") or None
        execution_id = str(getattr(canonical, "execution_id", "") or "") or None
        operation_type = str(
            consumer_operation_type
            or getattr(canonical, "operation_kind", "")
            or getattr(run, "operation_type", "")
            or ""
        )
        if canonical is None:
            return self._insufficient(
                consumer_phase_id,
                operation_type,
                plan_id=plan_id,
                reason="PHASE_DEPENDENCY_DOWNSTREAM_CANONICAL_PLAN_REQUIRED",
            )
        if not operation_type or operation_type == "unknown":
            return self._insufficient(
                consumer_phase_id,
                operation_type,
                plan_id=plan_id,
                execution_id=execution_id,
                reason="PHASE_DEPENDENCY_DOWNSTREAM_OPERATION_SEMANTICS_REQUIRED",
            )

        canonical_steps = list(getattr(canonical, "execution_steps", []) or [])
        selected_steps = (
            [step for step in canonical_steps if str(getattr(step, "step_id", "")) == source_step_id]
            if source_step_id
            else canonical_steps
        )
        if not selected_steps:
            return self._insufficient(
                consumer_phase_id,
                operation_type,
                plan_id=plan_id,
                execution_id=execution_id,
                reason="PHASE_DEPENDENCY_DOWNSTREAM_STEP_SEMANTICS_REQUIRED",
            )

        metadata = dict(getattr(canonical, "metadata", {}) or {})
        semantic_graph = metadata.get("semantic_intent_graph")
        semantic_graph = dict(semantic_graph) if isinstance(semantic_graph, dict) else {}
        if source_step_id is None and not self._has_semantic_intent(semantic_graph):
            return self._insufficient(
                consumer_phase_id,
                operation_type,
                plan_id=plan_id,
                execution_id=execution_id,
                reason="PHASE_DEPENDENCY_DOWNSTREAM_SEMANTIC_INTENT_REQUIRED",
            )
        source_payload = {
            "plan_id": plan_id,
            "execution_id": execution_id,
            "semantic_goal": getattr(canonical, "semantic_goal", None),
            "operation_kind": getattr(canonical, "operation_kind", None),
            "artifact_expectations": list(getattr(canonical, "artifact_expectations", []) or []),
            "validation_requirements": list(getattr(canonical, "validation_requirements", []) or []),
            "required_capabilities": list(getattr(canonical, "required_capabilities", []) or []),
            "policy_snapshot": dict(getattr(canonical, "policy_snapshot", {}) or {}),
            "semantic_intent_graph": semantic_graph,
            "steps": [step.model_dump(mode="json") for step in selected_steps],
        }
        source_sha256 = self._sha256(source_payload)
        plan_ref = f"canonical_execution_plan:{execution_id or plan_id}"
        step_refs = [f"canonical_execution_step:{step.step_id}" for step in selected_steps]
        provenance: list[RequirementProvenance] = []

        self._provenance(provenance, "operation_type", "canonical_execution_plan", plan_ref, "operation_kind", operation_type)
        self._provenance(
            provenance,
            "allowed_dependency_statuses",
            "system_invariant",
            "phase_semantic_demand_compiler:v1",
            "default_dependency_status",
            ["satisfied"],
        )
        self._provenance(
            provenance,
            "evidence_required",
            "system_invariant",
            "phase_semantic_demand_compiler:v1",
            "dependency_evidence_required",
            True,
        )

        required_use_safety: dict[str, list[Any]] = {}
        allowed_statuses = ["satisfied"]
        planning_intent = bool(semantic_graph.get("planning_intent"))
        knowledge_output = bool(semantic_graph.get("knowledge_output"))
        mutation_intent = bool(semantic_graph.get("mutation_intent"))
        execution_intent = bool(semantic_graph.get("execution_intent"))
        step_side_effect = any(bool(getattr(step, "side_effect", False)) for step in selected_steps)
        destructive_demand = mutation_intent or step_side_effect

        if planning_intent:
            required_use_safety["safe_for_planning"] = [True, "true_with_limitations"]
            self._provenance(
                provenance,
                "required_use_safety:safe_for_planning",
                "semantic_intent_graph",
                plan_ref,
                "planning_intent",
                True,
            )
            if not knowledge_output and not destructive_demand and not execution_intent:
                allowed_statuses.append("satisfied_with_limitations")
                self._provenance(
                    provenance,
                    "allowed_dependency_statuses",
                    "semantic_intent_graph",
                    plan_ref,
                    "planning_intent",
                    True,
                )
        if knowledge_output:
            required_use_safety["safe_for_truth_claim"] = [True]
            self._provenance(
                provenance,
                "required_use_safety:safe_for_truth_claim",
                "semantic_intent_graph",
                plan_ref,
                "knowledge_output",
                True,
            )
        if destructive_demand:
            required_use_safety["safe_for_destructive_action"] = [True]
            source_kind = "semantic_intent_graph" if mutation_intent else "canonical_execution_step"
            source_ref = plan_ref if mutation_intent else step_refs[0]
            source_field = "mutation_intent" if mutation_intent else "side_effect"
            self._provenance(
                provenance,
                "required_use_safety:safe_for_destructive_action",
                source_kind,
                source_ref,
                source_field,
                True,
            )

        prohibited_effects = [str(item) for item in semantic_graph.get("prohibited_effects", []) or [] if str(item)]
        readonly_contract = bool(semantic_graph.get("readonly_contract"))
        if readonly_contract and not destructive_demand:
            prohibited_effects.extend(["workspace_mutation", "destructive_action"])
        prohibited_effects = self._unique(prohibited_effects)
        for effect in prohibited_effects:
            self._provenance(
                provenance,
                f"prohibited_effect:{effect}",
                "semantic_intent_graph",
                plan_ref,
                "prohibited_effects" if effect in (semantic_graph.get("prohibited_effects") or []) else "readonly_contract",
                effect,
            )

        plan_capabilities = self._unique(list(getattr(canonical, "required_capabilities", []) or []))
        step_capabilities = self._unique(
            [
                capability
                for step in selected_steps
                for capability in list(getattr(step, "required_capabilities", []) or [])
            ]
        )
        required_capabilities = self._unique([*plan_capabilities, *step_capabilities])
        for capability in plan_capabilities:
            self._provenance(
                provenance,
                f"required_capability:{capability}",
                "canonical_execution_plan",
                plan_ref,
                "required_capabilities",
                capability,
            )
        for step, step_ref in zip(selected_steps, step_refs, strict=True):
            for capability in list(getattr(step, "required_capabilities", []) or []):
                self._provenance(
                    provenance,
                    f"required_capability:{capability}",
                    "canonical_execution_step",
                    step_ref,
                    "required_capabilities",
                    capability,
                )

        frozen_at = datetime.now(timezone.utc).isoformat()
        requirements = DownstreamPhaseRequirements(
            contract_id=f"compiled_phase_semantics:{source_sha256[:24]}",
            consumer_phase_id=consumer_phase_id,
            operation_type=operation_type,
            authority_source="compiled_task_semantics",
            allowed_dependency_statuses=self._unique(allowed_statuses),
            required_use_safety=required_use_safety,
            required_capabilities=required_capabilities,
            prohibited_effects=prohibited_effects,
            evidence_required=True,
            source_plan_id=plan_id,
            source_execution_id=execution_id,
            source_semantics_sha256=source_sha256,
            frozen_at=frozen_at,
            requirement_provenance=provenance,
        )
        invariant = self.system_invariants.resolve_invariants(consumer_phase_id, operation_type)
        if invariant is not None:
            requirements, merge_reason = self._strengthen(requirements, invariant)
            if merge_reason:
                return PhaseSemanticDemandCompilation(
                    status="blocked",
                    consumer_phase_id=consumer_phase_id,
                    consumer_operation_type=operation_type,
                    source_plan_id=plan_id,
                    source_execution_id=execution_id,
                    source_semantics_sha256=source_sha256,
                    reason_codes=[merge_reason],
                )
        missing_provenance = self._missing_provenance(requirements)
        if missing_provenance:
            return PhaseSemanticDemandCompilation(
                status="insufficient_contract_evidence",
                consumer_phase_id=consumer_phase_id,
                consumer_operation_type=operation_type,
                source_plan_id=plan_id,
                source_execution_id=execution_id,
                source_semantics_sha256=source_sha256,
                reason_codes=["PHASE_DEPENDENCY_REQUIREMENT_PROVENANCE_REQUIRED", *missing_provenance],
            )
        return PhaseSemanticDemandCompilation(
            status="compiled",
            consumer_phase_id=consumer_phase_id,
            consumer_operation_type=operation_type,
            source_plan_id=plan_id,
            source_execution_id=execution_id,
            source_semantics_sha256=source_sha256,
            requirements=requirements,
        )

    def _strengthen(
        self,
        compiled: DownstreamPhaseRequirements,
        invariant: DownstreamPhaseRequirements,
    ) -> tuple[DownstreamPhaseRequirements, str | None]:
        effective = compiled.model_copy(deep=True)
        allowed = [item for item in effective.allowed_dependency_statuses if item in invariant.allowed_dependency_statuses]
        if invariant.allowed_dependency_statuses and not allowed:
            return effective, "PHASE_DEPENDENCY_SYSTEM_INVARIANT_CONFLICT"
        if invariant.allowed_dependency_statuses:
            effective.allowed_dependency_statuses = allowed
        for field_name in ("required_use_safety", "required_semantic_properties"):
            target = getattr(effective, field_name)
            source = getattr(invariant, field_name)
            for name, values in source.items():
                if name in target:
                    intersection = [value for value in target[name] if value in values]
                    if not intersection:
                        return effective, "PHASE_DEPENDENCY_SYSTEM_INVARIANT_CONFLICT"
                    target[name] = intersection
                else:
                    target[name] = list(values)
        effective.required_downstream_uses = self._unique(
            [*effective.required_downstream_uses, *invariant.required_downstream_uses]
        )
        effective.required_capabilities = self._unique(
            [*effective.required_capabilities, *invariant.required_capabilities]
        )
        effective.base_constraints = self._unique([*effective.base_constraints, *invariant.base_constraints])
        effective.risk_constraints = self._unique([*effective.risk_constraints, *invariant.risk_constraints])
        effective.prohibited_effects = self._unique([*effective.prohibited_effects, *invariant.prohibited_effects])
        effective.evidence_required = effective.evidence_required or invariant.evidence_required
        effective.authorization_ttl_seconds = min(
            effective.authorization_ttl_seconds,
            invariant.authorization_ttl_seconds,
        )
        for limitation, impact in invariant.limitation_compatibility.items():
            existing = effective.limitation_compatibility.get(limitation)
            if existing is None or self._LIMITATION_STRENGTH[impact] > self._LIMITATION_STRENGTH[existing]:
                effective.limitation_compatibility[limitation] = impact
        invariant_sha256 = self._sha256(invariant.model_dump(mode="json"))
        for requirement in self._requirement_keys(invariant):
            effective.requirement_provenance.append(
                RequirementProvenance(
                    requirement=requirement,
                    source_kind="system_invariant",
                    source_ref=f"system_invariant:{invariant.contract_id}",
                    source_field=requirement,
                    source_sha256=invariant_sha256,
                )
            )
        effective.requirement_provenance.extend(item.model_copy(deep=True) for item in invariant.requirement_provenance)
        effective.authority_source = "compiled_task_semantics_with_system_invariants"
        return effective, None

    def _missing_provenance(self, requirements: DownstreamPhaseRequirements) -> list[str]:
        present = {item.requirement for item in requirements.requirement_provenance}
        return [f"missing_provenance:{item}" for item in self._requirement_keys(requirements) if item not in present]

    def _requirement_keys(self, requirements: DownstreamPhaseRequirements) -> list[str]:
        keys = ["operation_type", "allowed_dependency_statuses", "evidence_required"]
        keys.extend(f"required_downstream_use:{item}" for item in requirements.required_downstream_uses)
        keys.extend(f"required_use_safety:{item}" for item in requirements.required_use_safety)
        keys.extend(f"required_semantic_property:{item}" for item in requirements.required_semantic_properties)
        keys.extend(f"required_capability:{item}" for item in requirements.required_capabilities)
        keys.extend(f"limitation_compatibility:{item}" for item in requirements.limitation_compatibility)
        keys.extend(f"base_constraint:{item}" for item in requirements.base_constraints)
        keys.extend(f"risk_constraint:{item}" for item in requirements.risk_constraints)
        keys.extend(f"prohibited_effect:{item}" for item in requirements.prohibited_effects)
        return self._unique(keys)

    def _provenance(
        self,
        items: list[RequirementProvenance],
        requirement: str,
        source_kind: str,
        source_ref: str,
        source_field: str,
        source_value: Any,
    ) -> None:
        items.append(
            RequirementProvenance(
                requirement=requirement,
                source_kind=source_kind,  # type: ignore[arg-type]
                source_ref=source_ref,
                source_field=source_field,
                source_sha256=self._sha256(source_value),
            )
        )

    def _insufficient(
        self,
        phase_id: str,
        operation_type: str,
        *,
        plan_id: str | None,
        reason: str,
        execution_id: str | None = None,
    ) -> PhaseSemanticDemandCompilation:
        return PhaseSemanticDemandCompilation(
            status="insufficient_contract_evidence",
            consumer_phase_id=phase_id,
            consumer_operation_type=operation_type,
            source_plan_id=plan_id,
            source_execution_id=execution_id,
            reason_codes=[reason],
        )

    def _sha256(self, value: Any) -> str:
        payload = value.model_dump(mode="json") if hasattr(value, "model_dump") else value
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _has_semantic_intent(self, graph: dict[str, Any]) -> bool:
        signal_fields = (
            "observational_intent",
            "planning_intent",
            "mutation_intent",
            "execution_intent",
            "knowledge_output",
            "artifact_output",
            "readonly_contract",
            "state_effect",
            "workspace_effect",
            "filesystem_effect",
            "runtime_effect",
            "prohibited_effects",
            "requested_effects",
        )
        return any(graph.get(field) not in (None, False, "", "none", [], {}) for field in signal_fields)

    def _unique(self, values: list[str]) -> list[str]:
        return list(dict.fromkeys(str(item) for item in values if str(item)))
