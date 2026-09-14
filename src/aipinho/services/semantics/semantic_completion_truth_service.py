from __future__ import annotations

from collections import Counter
from typing import Any

from aipinho.schemas.semantics.semantic_truth_facet import SemanticTruthFacet
from aipinho.services.semantics.edge_semantic_demand_authority_service import (
    EdgeSemanticDemandAuthorityService,
)
from aipinho.services.semantics.offer_demand_compatibility_authority_service import (
    OfferDemandCompatibilityAuthorityService,
)
from aipinho.services.semantics.semantic_execution_graph_authority_service import (
    SemanticExecutionGraphAuthorityService,
)
from aipinho.services.semantics.semantic_nway_topology_authority_service import (
    SemanticNWayTopologyAuthorityService,
)
from aipinho.services.semantics.semantic_offer_authority_service import (
    SemanticOfferAuthorityService,
)
from aipinho.services.semantics.semantic_truth_facet_authority_service import (
    SemanticTruthFacetAuthorityService,
)


class SemanticCompletionTruthService:
    """Evaluates whether active semantic contracts support a success claim.

    This service is not SpeakerTruth authority. It produces one deterministic
    semantic facet for RuntimeTruthEngine to consume.
    """

    VERSION = "semantic_completion_truth.v1"

    def __init__(
        self,
        *,
        graph_authority: SemanticExecutionGraphAuthorityService | None = None,
        demand_authority: EdgeSemanticDemandAuthorityService | None = None,
        offer_authority: SemanticOfferAuthorityService | None = None,
        compatibility_authority: OfferDemandCompatibilityAuthorityService
        | None = None,
        nway_authority: SemanticNWayTopologyAuthorityService | None = None,
        facet_authority: SemanticTruthFacetAuthorityService | None = None,
    ) -> None:
        self.graph_authority = (
            graph_authority or SemanticExecutionGraphAuthorityService()
        )
        self.demand_authority = (
            demand_authority or EdgeSemanticDemandAuthorityService()
        )
        self.offer_authority = (
            offer_authority or SemanticOfferAuthorityService()
        )
        self.compatibility_authority = (
            compatibility_authority
            or OfferDemandCompatibilityAuthorityService()
        )
        self.nway_authority = (
            nway_authority or SemanticNWayTopologyAuthorityService()
        )
        self.facet_authority = (
            facet_authority or SemanticTruthFacetAuthorityService()
        )

    def evaluate(self, run: Any) -> SemanticTruthFacet:
        plan = getattr(run, "plan", None)
        graph = getattr(plan, "semantic_execution_graph", None)
        if graph is None:
            return self._freeze(
                status="not_applicable",
                safe=True,
                reason_codes=["semantic_graph_not_present"],
            )
        if not self.graph_authority.verify(graph):
            return self._freeze(
                status="blocked",
                safe=False,
                graph=graph,
                invalid_authority_refs=["semantic_execution_graph"],
                reason_codes=["SEMANTIC_TRUTH_GRAPH_AUTHORITY_INVALID"],
            )

        required_edges = sorted(
            [edge for edge in graph.edges if edge.required],
            key=lambda item: item.edge_id,
        )
        if not required_edges:
            return self._freeze(
                status="ready",
                safe=True,
                graph=graph,
                active_revision_id=getattr(
                    plan,
                    "active_semantic_graph_revision_id",
                    None,
                ),
                reason_codes=["semantic_required_edges_absent"],
            )

        projection = (
            plan.metadata.get("semantic_result_projection")
            if isinstance(getattr(plan, "metadata", None), dict)
            else None
        )
        if (
            isinstance(projection, dict)
            and projection.get("status") == "invalidated_by_graph_revision"
        ):
            return self._freeze(
                status="insufficient_evidence",
                safe=False,
                graph=graph,
                active_revision_id=getattr(
                    plan,
                    "active_semantic_graph_revision_id",
                    None,
                ),
                required_edge_ids=[
                    edge.edge_id for edge in required_edges
                ],
                unresolved_edge_ids=[
                    edge.edge_id for edge in required_edges
                ],
                reason_codes=[
                    "SEMANTIC_TRUTH_RESULT_PROJECTION_INVALIDATED"
                ],
            )

        edges_by_id = {edge.edge_id: edge for edge in graph.edges}
        demands = list(getattr(plan, "edge_semantic_demands", []) or [])
        offers = list(getattr(plan, "semantic_offers", []) or [])
        compatibilities = list(
            getattr(plan, "offer_demand_compatibilities", []) or []
        )
        joins = list(
            getattr(plan, "semantic_join_evaluations", []) or []
        )

        invalid: list[str] = []
        reason_codes: list[str] = []

        demand_counts = Counter(item.edge_id for item in demands)
        offer_counts = Counter(item.producer_work_unit_id for item in offers)
        compatibility_counts = Counter(
            item.edge_id for item in compatibilities
        )
        join_counts = Counter(
            item.consumer_work_unit_id for item in joins
        )
        if any(count > 1 for count in demand_counts.values()):
            invalid.append("duplicate_edge_demand")
        if any(count > 1 for count in offer_counts.values()):
            invalid.append("duplicate_work_unit_offer")
        if any(count > 1 for count in compatibility_counts.values()):
            invalid.append("duplicate_edge_compatibility")
        if any(count > 1 for count in join_counts.values()):
            invalid.append("duplicate_consumer_join")

        demands_by_edge = {}
        for demand in demands:
            if not self.demand_authority.verify(demand):
                invalid.append(f"demand:{demand.demand_id}")
                continue
            edge = edges_by_id.get(demand.edge_id)
            if (
                edge is None
                or demand.semantic_graph_id != graph.semantic_graph_id
                or demand.semantic_graph_authority_sha256
                != graph.authority_sha256
                or demand.producer_work_unit_id
                != edge.producer_work_unit_id
                or demand.consumer_work_unit_id
                != edge.consumer_work_unit_id
            ):
                invalid.append(f"demand_binding:{demand.demand_id}")
                continue
            demands_by_edge[demand.edge_id] = demand

        offers_by_unit = {}
        offers_by_id = {}
        for offer in offers:
            if not self.offer_authority.verify(offer):
                invalid.append(f"offer:{offer.offer_id}")
                continue
            if (
                offer.semantic_graph_id != graph.semantic_graph_id
                or offer.semantic_graph_authority_sha256
                != graph.authority_sha256
            ):
                invalid.append(f"offer_binding:{offer.offer_id}")
                continue
            offers_by_unit[offer.producer_work_unit_id] = offer
            offers_by_id[offer.offer_id] = offer

        compatibilities_by_edge = {}
        for compatibility in compatibilities:
            if not self.compatibility_authority.verify(compatibility):
                invalid.append(
                    f"compatibility:{compatibility.compatibility_id}"
                )
                continue
            edge = edges_by_id.get(compatibility.edge_id)
            demand = next(
                (
                    item
                    for item in demands
                    if item.demand_id == compatibility.demand_id
                ),
                None,
            )
            offer = offers_by_id.get(compatibility.offer_id)
            if (
                edge is None
                or demand is None
                or offer is None
                or compatibility.semantic_graph_id
                != graph.semantic_graph_id
                or compatibility.semantic_graph_authority_sha256
                != graph.authority_sha256
                or compatibility.producer_work_unit_id
                != edge.producer_work_unit_id
                or compatibility.consumer_work_unit_id
                != edge.consumer_work_unit_id
                or compatibility.demand_authority_sha256
                != demand.authority_sha256
                or compatibility.offer_authority_sha256
                != offer.authority_sha256
            ):
                invalid.append(
                    f"compatibility_binding:{compatibility.compatibility_id}"
                )
                continue
            compatibilities_by_edge[compatibility.edge_id] = compatibility

        joins_by_consumer = {}
        for join in joins:
            if not self.nway_authority.verify_join(join):
                invalid.append(f"join:{join.join_id}")
                continue
            if (
                join.semantic_graph_id != graph.semantic_graph_id
                or join.semantic_graph_authority_sha256
                != graph.authority_sha256
            ):
                invalid.append(f"join_binding:{join.join_id}")
                continue
            joins_by_consumer[join.consumer_work_unit_id] = join

        if invalid:
            return self._freeze(
                status="blocked",
                safe=False,
                graph=graph,
                active_revision_id=getattr(
                    plan,
                    "active_semantic_graph_revision_id",
                    None,
                ),
                required_edge_ids=[
                    edge.edge_id for edge in required_edges
                ],
                invalid_authority_refs=sorted(set(invalid)),
                reason_codes=["SEMANTIC_TRUTH_CONTRACT_AUTHORITY_INVALID"],
            )

        admitted: list[str] = []
        constrained: list[str] = []
        blocked: list[str] = []
        unresolved: list[str] = []
        partial_demands: list[str] = []
        disclosures: list[str] = []

        for edge in required_edges:
            demand = demands_by_edge.get(edge.edge_id)
            if demand is None:
                unresolved.append(edge.edge_id)
                continue
            if demand.status == "partial":
                partial_demands.append(edge.edge_id)
                unresolved.append(edge.edge_id)
                continue
            compatibility = compatibilities_by_edge.get(edge.edge_id)
            if compatibility is None:
                unresolved.append(edge.edge_id)
                continue
            if compatibility.decision == "blocked":
                blocked.append(edge.edge_id)
            elif compatibility.decision == "insufficient_evidence":
                unresolved.append(edge.edge_id)
            elif compatibility.decision == "admitted_with_constraints":
                constrained.append(edge.edge_id)
                disclosures.extend(compatibility.disclosures)
                disclosures.extend(compatibility.effective_constraints)
            elif compatibility.decision == "admitted":
                admitted.append(edge.edge_id)
            else:
                unresolved.append(edge.edge_id)

        incoming_required: dict[str, list[str]] = {}
        for edge in required_edges:
            incoming_required.setdefault(
                edge.consumer_work_unit_id,
                [],
            ).append(edge.edge_id)
        required_join_consumers = sorted(
            consumer_id
            for consumer_id, edge_ids in incoming_required.items()
            if len(edge_ids) > 1
        )
        constrained_joins: list[str] = []
        blocked_joins: list[str] = []
        unresolved_joins: list[str] = []
        for consumer_id in required_join_consumers:
            join = joins_by_consumer.get(consumer_id)
            if join is None:
                unresolved_joins.append(consumer_id)
                continue
            if sorted(join.required_edge_ids) != sorted(
                incoming_required[consumer_id]
            ):
                unresolved_joins.append(consumer_id)
                continue
            if join.decision == "blocked":
                blocked_joins.append(consumer_id)
            elif join.decision == "insufficient_evidence":
                unresolved_joins.append(consumer_id)
            elif join.decision == "admitted_with_constraints":
                constrained_joins.append(consumer_id)
                disclosures.extend(join.disclosures)
                disclosures.extend(join.effective_constraints)
            elif join.decision != "admitted":
                unresolved_joins.append(consumer_id)

        if blocked or blocked_joins:
            status = "blocked"
            reason_codes.append("SEMANTIC_TRUTH_REQUIRED_RELATION_BLOCKED")
        elif unresolved or unresolved_joins or partial_demands:
            status = "insufficient_evidence"
            reason_codes.append(
                "SEMANTIC_TRUTH_REQUIRED_RELATION_UNRESOLVED"
            )
        elif constrained or constrained_joins:
            status = "constrained"
            reason_codes.append(
                "SEMANTIC_TRUTH_SUCCESS_REQUIRES_DISCLOSURE"
            )
        else:
            status = "ready"
            reason_codes.append("SEMANTIC_TRUTH_READY")

        return self._freeze(
            status=status,
            safe=status == "ready",
            graph=graph,
            active_revision_id=getattr(
                plan,
                "active_semantic_graph_revision_id",
                None,
            ),
            required_edge_ids=[
                edge.edge_id for edge in required_edges
            ],
            admitted_edge_ids=admitted,
            constrained_edge_ids=constrained,
            blocked_edge_ids=blocked,
            unresolved_edge_ids=unresolved,
            partial_demand_edge_ids=partial_demands,
            required_join_consumer_ids=required_join_consumers,
            constrained_join_consumer_ids=constrained_joins,
            blocked_join_consumer_ids=blocked_joins,
            unresolved_join_consumer_ids=unresolved_joins,
            disclosures=disclosures,
            reason_codes=reason_codes,
        )

    def _freeze(
        self,
        *,
        status: str,
        safe: bool,
        graph: Any | None = None,
        active_revision_id: str | None = None,
        required_edge_ids: list[str] | None = None,
        admitted_edge_ids: list[str] | None = None,
        constrained_edge_ids: list[str] | None = None,
        blocked_edge_ids: list[str] | None = None,
        unresolved_edge_ids: list[str] | None = None,
        partial_demand_edge_ids: list[str] | None = None,
        required_join_consumer_ids: list[str] | None = None,
        constrained_join_consumer_ids: list[str] | None = None,
        blocked_join_consumer_ids: list[str] | None = None,
        unresolved_join_consumer_ids: list[str] | None = None,
        disclosures: list[str] | None = None,
        invalid_authority_refs: list[str] | None = None,
        reason_codes: list[str] | None = None,
    ) -> SemanticTruthFacet:
        facet = SemanticTruthFacet(
            facet_id="pending",
            status=status,
            safe_to_report_success=safe,
            semantic_graph_id=(
                getattr(graph, "semantic_graph_id", None)
                if graph is not None
                else None
            ),
            semantic_graph_authority_sha256=(
                getattr(graph, "authority_sha256", None)
                if graph is not None
                else None
            ),
            active_revision_id=active_revision_id,
            required_edge_ids=self._unique(required_edge_ids or []),
            admitted_edge_ids=self._unique(admitted_edge_ids or []),
            constrained_edge_ids=self._unique(
                constrained_edge_ids or []
            ),
            blocked_edge_ids=self._unique(blocked_edge_ids or []),
            unresolved_edge_ids=self._unique(
                unresolved_edge_ids or []
            ),
            partial_demand_edge_ids=self._unique(
                partial_demand_edge_ids or []
            ),
            required_join_consumer_ids=self._unique(
                required_join_consumer_ids or []
            ),
            constrained_join_consumer_ids=self._unique(
                constrained_join_consumer_ids or []
            ),
            blocked_join_consumer_ids=self._unique(
                blocked_join_consumer_ids or []
            ),
            unresolved_join_consumer_ids=self._unique(
                unresolved_join_consumer_ids or []
            ),
            disclosures=self._unique(disclosures or []),
            invalid_authority_refs=self._unique(
                invalid_authority_refs or []
            ),
            reason_codes=self._unique(reason_codes or []),
            authority_sha256="pending",
        )
        sha = self.facet_authority.compute_authority_sha256(facet)
        facet.authority_sha256 = sha
        facet.facet_id = f"semantic_truth_facet_{sha[:24]}"
        return facet

    def _unique(self, values: list[str]) -> list[str]:
        return list(
            dict.fromkeys(
                str(item)
                for item in values
                if str(item).strip()
            )
        )
