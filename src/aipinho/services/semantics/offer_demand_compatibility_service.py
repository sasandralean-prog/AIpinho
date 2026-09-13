from __future__ import annotations

from typing import Any

from aipinho.schemas.semantics.edge_semantic_demand import EdgeSemanticDemand
from aipinho.schemas.semantics.offer_demand_compatibility import (
    OfferDemandCompatibility,
    OfferDemandCompatibilityEvaluation,
)
from aipinho.schemas.semantics.semantic_offer import SemanticOffer
from aipinho.services.semantics.edge_semantic_demand_authority_service import (
    EdgeSemanticDemandAuthorityService,
)
from aipinho.services.semantics.offer_demand_compatibility_authority_service import (
    OfferDemandCompatibilityAuthorityService,
)
from aipinho.services.semantics.semantic_execution_graph_authority_service import (
    SemanticExecutionGraphAuthorityService,
)
from aipinho.services.semantics.semantic_offer_authority_service import (
    SemanticOfferAuthorityService,
)


class OfferDemandCompatibilityService:
    """Evaluates an immutable producer Offer against one immutable edge Demand."""

    VERSION = "offer_demand_compatibility.v1"

    def __init__(
        self,
        *,
        graph_authority: SemanticExecutionGraphAuthorityService | None = None,
        offer_authority: SemanticOfferAuthorityService | None = None,
        demand_authority: EdgeSemanticDemandAuthorityService | None = None,
        compatibility_authority: OfferDemandCompatibilityAuthorityService
        | None = None,
    ) -> None:
        self.graph_authority = (
            graph_authority or SemanticExecutionGraphAuthorityService()
        )
        self.offer_authority = (
            offer_authority or SemanticOfferAuthorityService()
        )
        self.demand_authority = (
            demand_authority or EdgeSemanticDemandAuthorityService()
        )
        self.compatibility_authority = (
            compatibility_authority
            or OfferDemandCompatibilityAuthorityService()
        )

    def evaluate(
        self,
        *,
        run: Any,
        offer: SemanticOffer,
        demand: EdgeSemanticDemand,
    ) -> OfferDemandCompatibilityEvaluation:
        graph = getattr(getattr(run, "plan", None), "semantic_execution_graph", None)
        if graph is None:
            return self._insufficient("OFFER_DEMAND_GRAPH_REQUIRED")
        if not self.graph_authority.verify(graph):
            return self._insufficient(
                "OFFER_DEMAND_GRAPH_AUTHORITY_INVALID"
            )
        if not self.offer_authority.verify(offer):
            return self._insufficient(
                "OFFER_DEMAND_OFFER_AUTHORITY_INVALID"
            )
        if not self.demand_authority.verify(demand):
            return self._insufficient(
                "OFFER_DEMAND_DEMAND_AUTHORITY_INVALID"
            )
        binding_reason = self._validate_binding(
            graph=graph,
            offer=offer,
            demand=demand,
        )
        if binding_reason:
            return self._insufficient(binding_reason)

        satisfied: list[str] = []
        blocked: list[str] = []
        unknown: list[str] = []
        constrained: list[str] = []

        if demand.status == "partial":
            unknown.append("demand:partial")

        for downstream_use in demand.required_downstream_uses:
            dimension = f"downstream_use:{downstream_use}"
            if downstream_use in offer.allowed_downstream_uses:
                satisfied.append(dimension)
            else:
                # Positive offer lists are open-world. Absence is unknown,
                # never an implicit negative observation.
                unknown.append(dimension)

        for name, acceptable in demand.required_use_safety.items():
            dimension = f"use_safety:{name}"
            if name not in offer.use_safety:
                unknown.append(dimension)
                continue
            observed = offer.use_safety[name]
            if observed in acceptable:
                satisfied.append(dimension)
            else:
                blocked.append(dimension)

        for name, acceptable in demand.required_semantic_properties.items():
            dimension = f"semantic_property:{name}"
            if name not in offer.semantic_properties:
                unknown.append(dimension)
                continue
            observed = offer.semantic_properties[name]
            if observed == "unknown":
                unknown.append(dimension)
            elif observed in acceptable:
                satisfied.append(dimension)
            else:
                blocked.append(dimension)

        for evidence_domain in demand.required_evidence_domains:
            dimension = f"evidence_domain:{evidence_domain}"
            if evidence_domain in offer.evidence_domains:
                satisfied.append(dimension)
            else:
                unknown.append(dimension)

        for effect in demand.required_upstream_effects:
            dimension = f"required_effect:{effect}"
            if effect in offer.observed_effects:
                satisfied.append(dimension)
            else:
                unknown.append(dimension)

        for effect in demand.prohibited_upstream_effects:
            dimension = f"prohibited_effect:{effect}"
            if effect in offer.observed_effects:
                blocked.append(dimension)
            else:
                # observed_effects is a positive observation set. Missing
                # effects remain unknown unless an explicit negative semantic
                # property exists in a future vocabulary revision.
                unknown.append(dimension)

        if demand.evidence_required:
            if offer.evidence_refs or offer.artifact_refs:
                satisfied.append("evidence:required")
            else:
                unknown.append("evidence:required")

        effective_constraints = self._unique(
            [
                *demand.base_constraints,
                *demand.risk_constraints,
                *offer.risk_constraints,
            ]
        )
        disclosures = self._unique(
            [
                *offer.required_disclosures,
                *[
                    f"limitation:{item}"
                    for item in offer.limitations
                ],
                *[
                    f"missing_truth:{item}"
                    for item in offer.missing_truth
                ],
            ]
        )
        if effective_constraints:
            constrained.extend(
                f"constraint:{item}" for item in effective_constraints
            )
        if disclosures:
            constrained.extend(
                f"disclosure:{item}" for item in disclosures
            )

        if blocked:
            decision = "blocked"
            reason_codes = ["OFFER_DEMAND_INCOMPATIBLE"]
        elif unknown:
            decision = "insufficient_evidence"
            reason_codes = ["OFFER_DEMAND_EVIDENCE_INSUFFICIENT"]
        elif constrained or offer.status == "partial":
            decision = "admitted_with_constraints"
            reason_codes = ["OFFER_DEMAND_COMPATIBLE_WITH_CONSTRAINTS"]
        else:
            decision = "admitted"
            reason_codes = ["OFFER_DEMAND_COMPATIBLE"]

        compatibility = OfferDemandCompatibility(
            compatibility_id="pending",
            edge_id=demand.edge_id,
            semantic_graph_id=graph.semantic_graph_id,
            semantic_graph_authority_sha256=graph.authority_sha256,
            producer_work_unit_id=demand.producer_work_unit_id,
            consumer_work_unit_id=demand.consumer_work_unit_id,
            offer_id=offer.offer_id,
            offer_authority_sha256=offer.authority_sha256,
            demand_id=demand.demand_id,
            demand_authority_sha256=demand.authority_sha256,
            decision=decision,
            satisfied_dimensions=self._unique(satisfied),
            constrained_dimensions=self._unique(constrained),
            blocked_dimensions=self._unique(blocked),
            unknown_dimensions=self._unique(unknown),
            effective_constraints=effective_constraints,
            disclosures=disclosures,
            reason_codes=reason_codes,
            authority_sha256="pending",
        )
        authority_sha256 = (
            self.compatibility_authority.compute_authority_sha256(
                compatibility
            )
        )
        compatibility.authority_sha256 = authority_sha256
        compatibility.compatibility_id = (
            f"offer_demand_compatibility_{authority_sha256[:24]}"
        )
        return OfferDemandCompatibilityEvaluation(
            status="evaluated",
            compatibility=compatibility,
        )

    def _validate_binding(
        self,
        *,
        graph: Any,
        offer: SemanticOffer,
        demand: EdgeSemanticDemand,
    ) -> str | None:
        if (
            offer.semantic_graph_id != graph.semantic_graph_id
            or demand.semantic_graph_id != graph.semantic_graph_id
        ):
            return "OFFER_DEMAND_GRAPH_ID_MISMATCH"
        if (
            offer.semantic_graph_authority_sha256 != graph.authority_sha256
            or demand.semantic_graph_authority_sha256 != graph.authority_sha256
        ):
            return "OFFER_DEMAND_GRAPH_HASH_MISMATCH"
        if offer.vocabulary_binding != demand.vocabulary_binding:
            return "OFFER_DEMAND_VOCABULARY_BINDING_MISMATCH"
        if offer.producer_work_unit_id != demand.producer_work_unit_id:
            return "OFFER_DEMAND_PRODUCER_MISMATCH"
        edge = next(
            (item for item in graph.edges if item.edge_id == demand.edge_id),
            None,
        )
        if edge is None:
            return "OFFER_DEMAND_EDGE_UNKNOWN"
        if (
            edge.producer_work_unit_id != demand.producer_work_unit_id
            or edge.consumer_work_unit_id != demand.consumer_work_unit_id
        ):
            return "OFFER_DEMAND_EDGE_BINDING_MISMATCH"
        return None

    def _unique(self, values: list[str]) -> list[str]:
        return list(dict.fromkeys(str(item) for item in values if str(item)))

    def _insufficient(
        self,
        reason: str,
    ) -> OfferDemandCompatibilityEvaluation:
        return OfferDemandCompatibilityEvaluation(
            status="insufficient_contract_evidence",
            reason_codes=[reason],
        )
