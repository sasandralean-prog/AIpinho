from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from aipinho.schemas.semantics.edge_semantic_demand import (
    EdgeSemanticDemandCandidate,
    EdgeSemanticDemandCompilation,
)
from aipinho.services.semantics.contract_bound_semantic_reasoner import (
    ContractBoundSemanticReasoner,
)
from aipinho.services.semantics.edge_semantic_demand_compiler_service import (
    EdgeSemanticDemandCompilerService,
)
from aipinho.services.semantics.task_semantic_vocabulary_authority_service import (
    TaskSemanticVocabularyAuthorityService,
)


class EdgeSemanticDemandInterpreterService:
    """Proposes missing edge-local requirements; deterministic compiler decides."""

    def __init__(
        self,
        *,
        reasoner: ContractBoundSemanticReasoner | None = None,
        compiler: EdgeSemanticDemandCompilerService | None = None,
        vocabulary_authority: TaskSemanticVocabularyAuthorityService | None = None,
    ) -> None:
        self.reasoner = reasoner
        self.compiler = compiler or EdgeSemanticDemandCompilerService()
        self.vocabulary_authority = (
            vocabulary_authority or TaskSemanticVocabularyAuthorityService()
        )

    def interpret_for_edge(
        self,
        *,
        run: Any,
        edge_id: str,
    ) -> EdgeSemanticDemandCompilation:
        explicit = self.compiler.compile_for_edge(run=run, edge_id=edge_id)
        if explicit.status != "compiled" or explicit.demand is None:
            return explicit
        if explicit.demand.status == "ready":
            explicit.semantic_interpretation = {
                "status": "not_required",
                "authority": "deterministic_edge_semantic_demand_gate",
            }
            return explicit

        plan = getattr(run, "plan", None)
        graph = getattr(plan, "semantic_execution_graph", None)
        vocabulary = getattr(plan, "task_semantic_vocabulary", None)
        canonical = getattr(plan, "canonical_execution_plan", None)
        if graph is None or vocabulary is None or canonical is None:
            return EdgeSemanticDemandCompilation(
                status="insufficient_contract_evidence",
                edge_id=edge_id,
                reason_codes=[
                    "EDGE_SEMANTIC_DEMAND_INTERPRETATION_CONTEXT_REQUIRED"
                ],
            )

        edge = next(
            (item for item in graph.edges if item.edge_id == edge_id),
            None,
        )
        if edge is None:
            return EdgeSemanticDemandCompilation(
                status="insufficient_contract_evidence",
                edge_id=edge_id,
                reason_codes=["EDGE_SEMANTIC_DEMAND_EDGE_UNKNOWN"],
            )
        units = {item.work_unit_id: item for item in graph.work_units}
        producer = units.get(edge.producer_work_unit_id)
        consumer = units.get(edge.consumer_work_unit_id)
        if producer is None or consumer is None:
            return EdgeSemanticDemandCompilation(
                status="insufficient_contract_evidence",
                edge_id=edge_id,
                reason_codes=["EDGE_SEMANTIC_DEMAND_WORK_UNIT_UNKNOWN"],
            )

        governed = self.vocabulary_authority.governed_view(vocabulary)
        steps_by_id = {
            step.step_id: step for step in canonical.execution_steps
        }
        consumer_steps = [
            steps_by_id[step_id].model_dump(mode="json")
            for step_id in consumer.source_step_ids
            if step_id in steps_by_id
        ]
        reasoner = self.reasoner or ContractBoundSemanticReasoner()
        self.reasoner = reasoner
        proposal = reasoner.propose_json(
            semantic_goal=(
                "Determine the minimum semantic guarantees this consumer needs "
                "from this producer on this exact dependency edge. "
                "Do not infer producer truth or authorize execution."
            ),
            payload={
                "edge": edge.model_dump(mode="json"),
                "producer_work_unit": producer.model_dump(mode="json"),
                "consumer_work_unit": consumer.model_dump(mode="json"),
                "consumer_source_steps": consumer_steps,
                "existing_partial_demand": explicit.demand.model_dump(mode="json"),
                "governed_vocabulary": {
                    "downstream_use_identifiers": governed.get(
                        "downstream_use_identifiers", []
                    ),
                    "use_safety_requirement_states": governed.get(
                        "use_safety_requirement_states", {}
                    ),
                    "semantic_property_requirement_states": governed.get(
                        "semantic_property_requirement_states", {}
                    ),
                    "evidence_domain_identifiers": governed.get(
                        "evidence_domain_identifiers", []
                    ),
                    "effect_identifiers": governed.get(
                        "effect_identifiers", []
                    ),
                    "constraint_families": governed.get(
                        "constraint_families", []
                    ),
                },
                "output_schema": {
                    "required_downstream_uses": ["governed_identifier"],
                    "required_use_safety": {
                        "governed_safe_for_dimension": [
                            "governed_requirement_state"
                        ]
                    },
                    "required_semantic_properties": {
                        "governed_property": ["governed_requirement_state"]
                    },
                    "required_evidence_domains": ["governed_identifier"],
                    "required_upstream_effects": ["governed_identifier"],
                    "prohibited_upstream_effects": ["governed_identifier"],
                    "evidence_required": "boolean",
                    "base_constraints": ["governed_constraint"],
                    "risk_constraints": ["governed_constraint"],
                    "confidence": "number_between_0_and_1",
                    "rationale": "non_empty_string",
                },
                "rules": [
                    "Demand is consumer-local and edge-local.",
                    "Demand describes need, never observed producer truth.",
                    "Use only governed identifiers and states.",
                    "Do not invent capabilities, properties, uses, effects or evidence domains.",
                    "Do not weaken any explicit consumer requirement.",
                    "For evidence_dependency or validation_dependency, evidence_required must remain true.",
                    "Prefer the minimum sufficient requirements.",
                    "If no governed identifier represents a required concept, leave it empty and lower confidence.",
                    "Do not use phase number, filename, deliverable name or node position as authority.",
                ],
            },
            allowed_fields=[
                "required_downstream_uses",
                "required_use_safety",
                "required_semantic_properties",
                "required_evidence_domains",
                "required_upstream_effects",
                "prohibited_upstream_effects",
                "evidence_required",
                "base_constraints",
                "risk_constraints",
                "confidence",
                "rationale",
            ],
            required_fields=[
                "required_downstream_uses",
                "required_use_safety",
                "required_semantic_properties",
                "required_evidence_domains",
                "required_upstream_effects",
                "prohibited_upstream_effects",
                "evidence_required",
                "base_constraints",
                "risk_constraints",
                "confidence",
                "rationale",
            ],
        )
        provenance = {
            "model_id": proposal.get("model_id"),
            "response_id": proposal.get("response_id"),
            "real_inference": proposal.get("real_inference"),
            "evaluation_status": proposal.get("evaluation_status"),
            "warnings": list(proposal.get("warnings") or []),
            "authority": "deterministic_edge_semantic_demand_gate",
        }
        if proposal.get("status") != "candidate":
            return EdgeSemanticDemandCompilation(
                status="insufficient_contract_evidence",
                edge_id=edge_id,
                reason_codes=[
                    str(
                        proposal.get("reason_code")
                        or "EDGE_SEMANTIC_DEMAND_MODEL_UNAVAILABLE"
                    )
                ],
                semantic_interpretation=provenance,
            )
        try:
            candidate = EdgeSemanticDemandCandidate.model_validate(
                proposal.get("candidate") or {}
            )
        except ValidationError:
            return EdgeSemanticDemandCompilation(
                status="insufficient_contract_evidence",
                edge_id=edge_id,
                reason_codes=[
                    "EDGE_SEMANTIC_DEMAND_CANDIDATE_INVALID"
                ],
                semantic_interpretation={
                    **provenance,
                    "candidate": dict(proposal.get("candidate") or {}),
                },
            )

        return self.compiler.compile_candidate_for_edge(
            run=run,
            edge_id=edge_id,
            candidate=candidate,
            provenance=provenance,
        )
