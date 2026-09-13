from __future__ import annotations

import re
from typing import Any

from aipinho.schemas.semantics.edge_semantic_demand import (
    EdgeSemanticDemand,
    EdgeSemanticDemandCandidate,
    EdgeSemanticDemandCompilation,
)
from aipinho.services.semantics.edge_semantic_demand_authority_service import (
    EdgeSemanticDemandAuthorityService,
)
from aipinho.services.semantics.semantic_execution_graph_authority_service import (
    SemanticExecutionGraphAuthorityService,
)
from aipinho.services.semantics.task_semantic_vocabulary_authority_service import (
    TaskSemanticVocabularyAuthorityService,
)


class EdgeSemanticDemandCompilerService:
    """Compiles consumer-local requirements for one semantic graph edge."""

    VERSION = "edge_semantic_demand_compiler.v1"

    def __init__(
        self,
        *,
        graph_authority: SemanticExecutionGraphAuthorityService | None = None,
        vocabulary_authority: TaskSemanticVocabularyAuthorityService | None = None,
        demand_authority: EdgeSemanticDemandAuthorityService | None = None,
    ) -> None:
        self.graph_authority = (
            graph_authority or SemanticExecutionGraphAuthorityService()
        )
        self.vocabulary_authority = (
            vocabulary_authority or TaskSemanticVocabularyAuthorityService()
        )
        self.demand_authority = (
            demand_authority or EdgeSemanticDemandAuthorityService()
        )

    def compile_for_edge(
        self,
        *,
        run: Any,
        edge_id: str,
    ) -> EdgeSemanticDemandCompilation:
        context, reason = self._context(run=run, edge_id=edge_id)
        if reason:
            return self._insufficient(edge_id=edge_id, reason=reason)
        assert context is not None

        edge = context["edge"]
        consumer = context["consumer"]
        view = context["vocabulary_view"]

        explicit = self._collect_explicit_requirements(
            context=context,
            consumer_step_ids=consumer.source_step_ids,
        )
        reason = self._validate_requirements(explicit, view=view)
        if reason:
            return EdgeSemanticDemandCompilation(
                status="blocked",
                edge_id=edge_id,
                reason_codes=[reason],
            )

        evidence_explicit = explicit["evidence_required_values"]
        if evidence_explicit:
            if len(set(evidence_explicit)) != 1:
                return EdgeSemanticDemandCompilation(
                    status="blocked",
                    edge_id=edge_id,
                    reason_codes=[
                        "EDGE_SEMANTIC_DEMAND_EVIDENCE_REQUIREMENT_CONFLICT"
                    ],
                )
            evidence_required = bool(evidence_explicit[0])
        else:
            evidence_required = edge.relation in {
                "evidence_dependency",
                "validation_dependency",
            }

        semantic_requirement_present = any(
            [
                explicit["required_downstream_uses"],
                explicit["required_use_safety"],
                explicit["required_semantic_properties"],
                explicit["required_evidence_domains"],
                explicit["required_upstream_effects"],
                explicit["prohibited_upstream_effects"],
                explicit["base_constraints"],
                explicit["risk_constraints"],
            ]
        )

        reason_codes: list[str] = []
        status = "ready"
        if (
            edge.relation == "semantic_dependency"
            and not semantic_requirement_present
        ):
            status = "partial"
            reason_codes.append(
                "edge_semantic_requirements_unspecified"
            )
        elif (
            edge.relation in {"evidence_dependency", "validation_dependency"}
            and not explicit["required_evidence_domains"]
            and not semantic_requirement_present
        ):
            status = "partial"
            reason_codes.append(
                "edge_evidence_domain_unspecified"
            )

        demand = EdgeSemanticDemand(
            demand_id="pending",
            edge_id=edge.edge_id,
            semantic_graph_id=context["graph"].semantic_graph_id,
            semantic_graph_authority_sha256=context["graph"].authority_sha256,
            producer_work_unit_id=edge.producer_work_unit_id,
            consumer_work_unit_id=edge.consumer_work_unit_id,
            vocabulary_binding=context["vocabulary"].binding(),
            status=status,
            consumer_required_capabilities=list(
                consumer.required_capabilities
            ),
            required_downstream_uses=explicit[
                "required_downstream_uses"
            ],
            required_use_safety=explicit["required_use_safety"],
            required_semantic_properties=explicit[
                "required_semantic_properties"
            ],
            required_evidence_domains=explicit[
                "required_evidence_domains"
            ],
            required_upstream_effects=explicit[
                "required_upstream_effects"
            ],
            prohibited_upstream_effects=explicit[
                "prohibited_upstream_effects"
            ],
            evidence_required=evidence_required,
            base_constraints=explicit["base_constraints"],
            risk_constraints=explicit["risk_constraints"],
            source_consumer_step_ids=list(consumer.source_step_ids),
            source_refs=explicit["source_refs"],
            reason_codes=reason_codes,
            authority_sha256="pending",
        )
        authority_sha256 = self.demand_authority.compute_authority_sha256(
            demand
        )
        demand.authority_sha256 = authority_sha256
        demand.demand_id = f"edge_semantic_demand_{authority_sha256[:24]}"
        # demand_id is intentionally outside the authority payload; it derives
        # from the authority hash rather than participating in it.

        return EdgeSemanticDemandCompilation(
            status="compiled",
            edge_id=edge.edge_id,
            demand=demand,
        )

    def compile_candidate_for_edge(
        self,
        *,
        run: Any,
        edge_id: str,
        candidate: EdgeSemanticDemandCandidate,
        provenance: dict[str, Any] | None = None,
    ) -> EdgeSemanticDemandCompilation:
        context, reason = self._context(run=run, edge_id=edge_id)
        if reason:
            return self._insufficient(edge_id=edge_id, reason=reason)
        assert context is not None

        if candidate.confidence < 0.65:
            return EdgeSemanticDemandCompilation(
                status="insufficient_contract_evidence",
                edge_id=edge_id,
                reason_codes=[
                    "EDGE_SEMANTIC_DEMAND_INTERPRETATION_CONFIDENCE_INSUFFICIENT"
                ],
                semantic_interpretation=dict(provenance or {}),
            )
        if not candidate.rationale.strip():
            return EdgeSemanticDemandCompilation(
                status="insufficient_contract_evidence",
                edge_id=edge_id,
                reason_codes=[
                    "EDGE_SEMANTIC_DEMAND_INTERPRETATION_RATIONALE_REQUIRED"
                ],
                semantic_interpretation=dict(provenance or {}),
            )

        explicit = self._collect_explicit_requirements(
            context=context,
            consumer_step_ids=context["consumer"].source_step_ids,
        )
        if (
            context["edge"].relation
            in {"evidence_dependency", "validation_dependency"}
            and candidate.evidence_required is not True
        ):
            return EdgeSemanticDemandCompilation(
                status="blocked",
                edge_id=edge_id,
                reason_codes=[
                    "EDGE_SEMANTIC_DEMAND_EVIDENCE_REQUIREMENT_WEAKENING"
                ],
                semantic_interpretation=dict(provenance or {}),
            )
        candidate_payload = {
            "required_downstream_uses": list(
                candidate.required_downstream_uses
            ),
            "required_use_safety": dict(candidate.required_use_safety),
            "required_semantic_properties": dict(
                candidate.required_semantic_properties
            ),
            "required_evidence_domains": list(
                candidate.required_evidence_domains
            ),
            "required_upstream_effects": list(
                candidate.required_upstream_effects
            ),
            "prohibited_upstream_effects": list(
                candidate.prohibited_upstream_effects
            ),
            "base_constraints": list(candidate.base_constraints),
            "risk_constraints": list(candidate.risk_constraints),
        }
        reason = self._validate_requirements(
            {
                **candidate_payload,
                "evidence_required_values": [candidate.evidence_required],
                "source_refs": [],
            },
            view=context["vocabulary_view"],
        )
        if reason:
            return EdgeSemanticDemandCompilation(
                status="blocked",
                edge_id=edge_id,
                reason_codes=[reason],
                semantic_interpretation=dict(provenance or {}),
            )

        merged, merge_reason = self._merge_candidate_with_explicit(
            explicit=explicit,
            candidate=candidate,
        )
        if merge_reason:
            return EdgeSemanticDemandCompilation(
                status="blocked",
                edge_id=edge_id,
                reason_codes=[merge_reason],
                semantic_interpretation=dict(provenance or {}),
            )

        demand = self._freeze_from_requirements(
            context=context,
            requirements=merged,
            interpreted=True,
        )
        return EdgeSemanticDemandCompilation(
            status="compiled",
            edge_id=edge_id,
            demand=demand,
            semantic_interpretation={
                **dict(provenance or {}),
                "candidate": candidate.model_dump(mode="json"),
                "rationale": candidate.rationale,
                "confidence": candidate.confidence,
                "authority": "deterministic_edge_semantic_demand_gate",
            },
        )

    def _merge_candidate_with_explicit(
        self,
        *,
        explicit: dict[str, Any],
        candidate: EdgeSemanticDemandCandidate,
    ) -> tuple[dict[str, Any], str | None]:
        merged_use_safety, reason = self._merge_requirement_mapping(
            explicit["required_use_safety"],
            candidate.required_use_safety,
        )
        if reason:
            return {}, reason
        merged_properties, reason = self._merge_requirement_mapping(
            explicit["required_semantic_properties"],
            candidate.required_semantic_properties,
        )
        if reason:
            return {}, reason

        evidence_explicit = list(explicit["evidence_required_values"])
        if evidence_explicit:
            if len(set(evidence_explicit)) != 1:
                return {}, "EDGE_SEMANTIC_DEMAND_EVIDENCE_REQUIREMENT_CONFLICT"
            evidence_required = bool(evidence_explicit[0])
            if evidence_required != candidate.evidence_required:
                return {}, "EDGE_SEMANTIC_DEMAND_MODEL_EXPLICIT_CONFLICT"
        else:
            evidence_required = candidate.evidence_required

        required_effects = self._unique(
            [
                *explicit["required_upstream_effects"],
                *candidate.required_upstream_effects,
            ]
        )
        prohibited_effects = self._unique(
            [
                *explicit["prohibited_upstream_effects"],
                *candidate.prohibited_upstream_effects,
            ]
        )
        if set(required_effects).intersection(prohibited_effects):
            return {}, "EDGE_SEMANTIC_DEMAND_EFFECT_CONFLICT"

        return {
            "required_downstream_uses": self._unique(
                [
                    *explicit["required_downstream_uses"],
                    *candidate.required_downstream_uses,
                ]
            ),
            "required_use_safety": merged_use_safety,
            "required_semantic_properties": merged_properties,
            "required_evidence_domains": self._unique(
                [
                    *explicit["required_evidence_domains"],
                    *candidate.required_evidence_domains,
                ]
            ),
            "required_upstream_effects": required_effects,
            "prohibited_upstream_effects": prohibited_effects,
            "base_constraints": self._unique(
                [
                    *explicit["base_constraints"],
                    *candidate.base_constraints,
                ]
            ),
            "risk_constraints": self._unique(
                [
                    *explicit["risk_constraints"],
                    *candidate.risk_constraints,
                ]
            ),
            "evidence_required_values": [evidence_required],
            "source_refs": self._unique(
                [
                    *explicit["source_refs"],
                    "semantic_reasoner_candidate",
                ]
            ),
        }, None

    def _merge_requirement_mapping(
        self,
        explicit: dict[str, list[Any]],
        candidate: dict[str, list[Any]],
    ) -> tuple[dict[str, list[Any]], str | None]:
        merged = {
            key: list(values)
            for key, values in explicit.items()
        }
        for key, values in candidate.items():
            normalized = list(dict.fromkeys(values))
            if key in merged and merged[key] != normalized:
                return {}, "EDGE_SEMANTIC_DEMAND_MODEL_EXPLICIT_CONFLICT"
            merged[key] = normalized
        return dict(sorted(merged.items())), None

    def _freeze_from_requirements(
        self,
        *,
        context: dict[str, Any],
        requirements: dict[str, Any],
        interpreted: bool,
    ) -> EdgeSemanticDemand:
        edge = context["edge"]
        consumer = context["consumer"]
        semantic_requirement_present = any(
            [
                requirements["required_downstream_uses"],
                requirements["required_use_safety"],
                requirements["required_semantic_properties"],
                requirements["required_evidence_domains"],
                requirements["required_upstream_effects"],
                requirements["prohibited_upstream_effects"],
                requirements["base_constraints"],
                requirements["risk_constraints"],
            ]
        )
        reason_codes: list[str] = []
        status = "ready"
        if (
            edge.relation == "semantic_dependency"
            and not semantic_requirement_present
        ):
            status = "partial"
            reason_codes.append("edge_semantic_requirements_unspecified")
        elif (
            edge.relation in {"evidence_dependency", "validation_dependency"}
            and not requirements["required_evidence_domains"]
            and not semantic_requirement_present
        ):
            status = "partial"
            reason_codes.append("edge_evidence_domain_unspecified")

        demand = EdgeSemanticDemand(
            demand_id="pending",
            edge_id=edge.edge_id,
            semantic_graph_id=context["graph"].semantic_graph_id,
            semantic_graph_authority_sha256=context["graph"].authority_sha256,
            producer_work_unit_id=edge.producer_work_unit_id,
            consumer_work_unit_id=edge.consumer_work_unit_id,
            vocabulary_binding=context["vocabulary"].binding(),
            status=status,
            consumer_required_capabilities=list(
                consumer.required_capabilities
            ),
            required_downstream_uses=list(
                requirements["required_downstream_uses"]
            ),
            required_use_safety=dict(requirements["required_use_safety"]),
            required_semantic_properties=dict(
                requirements["required_semantic_properties"]
            ),
            required_evidence_domains=list(
                requirements["required_evidence_domains"]
            ),
            required_upstream_effects=list(
                requirements["required_upstream_effects"]
            ),
            prohibited_upstream_effects=list(
                requirements["prohibited_upstream_effects"]
            ),
            evidence_required=bool(
                list(requirements["evidence_required_values"] or [False])[0]
            ),
            base_constraints=list(requirements["base_constraints"]),
            risk_constraints=list(requirements["risk_constraints"]),
            source_consumer_step_ids=list(consumer.source_step_ids),
            source_refs=list(requirements["source_refs"]),
            reason_codes=reason_codes,
            authority_sha256="pending",
        )
        authority_sha256 = self.demand_authority.compute_authority_sha256(
            demand
        )
        demand.authority_sha256 = authority_sha256
        demand.demand_id = f"edge_semantic_demand_{authority_sha256[:24]}"
        return demand

    def _context(
        self,
        *,
        run: Any,
        edge_id: str,
    ) -> tuple[dict[str, Any] | None, str | None]:
        plan = getattr(run, "plan", None)
        graph = getattr(plan, "semantic_execution_graph", None)
        vocabulary = getattr(plan, "task_semantic_vocabulary", None)
        canonical = getattr(plan, "canonical_execution_plan", None)
        if graph is None:
            return None, "EDGE_SEMANTIC_DEMAND_GRAPH_REQUIRED"
        if not self.graph_authority.verify(graph):
            return None, "EDGE_SEMANTIC_DEMAND_GRAPH_AUTHORITY_INVALID"
        if vocabulary is None:
            return None, "EDGE_SEMANTIC_DEMAND_VOCABULARY_REQUIRED"
        if not self.vocabulary_authority.verify(vocabulary):
            return None, "EDGE_SEMANTIC_DEMAND_VOCABULARY_AUTHORITY_INVALID"
        if graph.vocabulary_binding != vocabulary.binding():
            return None, "EDGE_SEMANTIC_DEMAND_VOCABULARY_BINDING_MISMATCH"
        if canonical is None:
            return None, "EDGE_SEMANTIC_DEMAND_CANONICAL_PLAN_REQUIRED"

        edges = {item.edge_id: item for item in graph.edges}
        edge = edges.get(edge_id)
        if edge is None:
            return None, "EDGE_SEMANTIC_DEMAND_EDGE_UNKNOWN"
        work_units = {
            item.work_unit_id: item for item in graph.work_units
        }
        producer = work_units.get(edge.producer_work_unit_id)
        consumer = work_units.get(edge.consumer_work_unit_id)
        if producer is None or consumer is None:
            return None, "EDGE_SEMANTIC_DEMAND_WORK_UNIT_UNKNOWN"

        steps_by_id = {
            step.step_id: step for step in canonical.execution_steps
        }

        return {
            "run": run,
            "plan": plan,
            "graph": graph,
            "vocabulary": vocabulary,
            "vocabulary_view": self.vocabulary_authority.governed_view(
                vocabulary
            ),
            "canonical": canonical,
            "steps_by_id": steps_by_id,
            "edge": edge,
            "producer": producer,
            "consumer": consumer,
        }, None

    def _collect_explicit_requirements(
        self,
        *,
        context: dict[str, Any],
        consumer_step_ids: list[str],
    ) -> dict[str, Any]:
        downstream_uses: list[str] = []
        use_safety: dict[str, list[Any]] = {}
        semantic_properties: dict[str, list[Any]] = {}
        evidence_domains: list[str] = []
        required_effects: list[str] = []
        prohibited_effects: list[str] = []
        base_constraints: list[str] = []
        risk_constraints: list[str] = []
        evidence_values: list[bool] = []
        source_refs: list[str] = []

        for step_id in consumer_step_ids:
            step = context["steps_by_id"].get(step_id)
            if step is None:
                continue
            metadata = dict(step.metadata or {})
            ref = f"canonical_execution_step:{step_id}"
            self._extend_list(
                downstream_uses,
                metadata.get("required_downstream_uses"),
            )
            self._merge_mapping(
                use_safety,
                metadata.get("required_use_safety"),
            )
            self._merge_mapping(
                semantic_properties,
                metadata.get("required_semantic_properties"),
            )
            self._extend_list(
                evidence_domains,
                metadata.get("required_evidence_domains"),
            )
            self._extend_list(
                required_effects,
                metadata.get("required_upstream_effects"),
            )
            self._extend_list(
                prohibited_effects,
                metadata.get("prohibited_upstream_effects"),
            )
            self._extend_list(
                base_constraints,
                metadata.get("base_constraints"),
            )
            self._extend_list(
                risk_constraints,
                metadata.get("risk_constraints"),
            )
            if isinstance(metadata.get("evidence_required"), bool):
                evidence_values.append(metadata["evidence_required"])

            typed_fields = {
                "required_downstream_uses",
                "required_use_safety",
                "required_semantic_properties",
                "required_evidence_domains",
                "required_upstream_effects",
                "prohibited_upstream_effects",
                "base_constraints",
                "risk_constraints",
                "evidence_required",
            }
            if any(field in metadata for field in typed_fields):
                source_refs.append(ref)

        return {
            "required_downstream_uses": self._unique(downstream_uses),
            "required_use_safety": self._normalized_mapping(use_safety),
            "required_semantic_properties": self._normalized_mapping(
                semantic_properties
            ),
            "required_evidence_domains": self._unique(evidence_domains),
            "required_upstream_effects": self._unique(required_effects),
            "prohibited_upstream_effects": self._unique(
                prohibited_effects
            ),
            "base_constraints": self._unique(base_constraints),
            "risk_constraints": self._unique(risk_constraints),
            "evidence_required_values": evidence_values,
            "source_refs": self._unique(source_refs),
        }

    def _validate_requirements(
        self,
        explicit: dict[str, Any],
        *,
        view: dict[str, Any],
    ) -> str | None:
        allowed_downstream = set(
            view.get("downstream_use_identifiers") or []
        )
        if any(
            item not in allowed_downstream
            for item in explicit["required_downstream_uses"]
        ):
            return "EDGE_SEMANTIC_DEMAND_DOWNSTREAM_USE_UNGOVERNED"

        safety_states = dict(
            view.get("use_safety_requirement_states") or {}
        )
        for name, values in explicit["required_use_safety"].items():
            allowed = list(safety_states.get(name) or [])
            if not allowed or any(value not in allowed for value in values):
                return "EDGE_SEMANTIC_DEMAND_USE_SAFETY_INVALID"

        property_states = dict(
            view.get("semantic_property_requirement_states") or {}
        )
        for name, values in explicit[
            "required_semantic_properties"
        ].items():
            allowed = list(property_states.get(name) or [])
            if not allowed or any(value not in allowed for value in values):
                return "EDGE_SEMANTIC_DEMAND_SEMANTIC_PROPERTY_INVALID"

        allowed_evidence = set(
            view.get("evidence_domain_identifiers") or []
        )
        if any(
            item not in allowed_evidence
            for item in explicit["required_evidence_domains"]
        ):
            return "EDGE_SEMANTIC_DEMAND_EVIDENCE_DOMAIN_UNGOVERNED"

        allowed_effects = set(view.get("effect_identifiers") or [])
        if any(
            item not in allowed_effects
            for item in [
                *explicit["required_upstream_effects"],
                *explicit["prohibited_upstream_effects"],
            ]
        ):
            return "EDGE_SEMANTIC_DEMAND_EFFECT_UNGOVERNED"

        families = set(view.get("constraint_families") or [])
        if any(
            not self._valid_constraint(item, families=families)
            for item in [
                *explicit["base_constraints"],
                *explicit["risk_constraints"],
            ]
        ):
            return "EDGE_SEMANTIC_DEMAND_CONSTRAINT_INVALID"
        return None

    def _valid_constraint(
        self,
        value: str,
        *,
        families: set[str],
    ) -> bool:
        if re.fullmatch(r"[a-z][a-z0-9_]*", value) is None:
            return False
        return any(value.startswith(f"{family}_") for family in families)

    def _extend_list(self, target: list[str], value: Any) -> None:
        if isinstance(value, list):
            target.extend(
                str(item) for item in value if str(item).strip()
            )

    def _merge_mapping(
        self,
        target: dict[str, list[Any]],
        value: Any,
    ) -> None:
        if not isinstance(value, dict):
            return
        for key, raw_values in value.items():
            if not isinstance(raw_values, list):
                continue
            bucket = target.setdefault(str(key), [])
            bucket.extend(raw_values)

    def _normalized_mapping(
        self,
        value: dict[str, list[Any]],
    ) -> dict[str, list[Any]]:
        return {
            key: list(dict.fromkeys(values))
            for key, values in sorted(value.items())
        }

    def _unique(self, values: list[str]) -> list[str]:
        return list(dict.fromkeys(values))

    def _insufficient(
        self,
        *,
        edge_id: str,
        reason: str,
    ) -> EdgeSemanticDemandCompilation:
        return EdgeSemanticDemandCompilation(
            status="insufficient_contract_evidence",
            edge_id=edge_id or None,
            reason_codes=[reason],
        )
