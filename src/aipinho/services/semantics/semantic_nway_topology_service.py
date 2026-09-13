from __future__ import annotations

from typing import Any

from aipinho.schemas.semantics.semantic_nway_topology import (
    SemanticJoinEvaluation,
    SemanticJoinEvaluationResult,
    SemanticTopologyEdgeState,
    SemanticTopologyNeighborhood,
)
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


class SemanticNWayTopologyService:
    """Projects fan-in/fan-out and evaluates joins without positional semantics."""

    VERSION = "semantic_nway_topology.v1"

    def __init__(
        self,
        *,
        graph_authority: SemanticExecutionGraphAuthorityService | None = None,
        demand_authority: EdgeSemanticDemandAuthorityService | None = None,
        offer_authority: SemanticOfferAuthorityService | None = None,
        compatibility_authority: OfferDemandCompatibilityAuthorityService
        | None = None,
        topology_authority: SemanticNWayTopologyAuthorityService | None = None,
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
        self.topology_authority = (
            topology_authority
            or SemanticNWayTopologyAuthorityService()
        )

    def neighborhood(
        self,
        *,
        run: Any,
        work_unit_id: str,
    ) -> SemanticTopologyNeighborhood | None:
        context, reason = self._context(run)
        if reason or context is None:
            return None
        graph = context["graph"]
        if work_unit_id not in context["work_units"]:
            return None

        incoming = [
            edge for edge in graph.edges
            if edge.consumer_work_unit_id == work_unit_id
        ]
        outgoing = [
            edge for edge in graph.edges
            if edge.producer_work_unit_id == work_unit_id
        ]
        incoming_states = [
            self._edge_state(context, edge)
            for edge in sorted(incoming, key=lambda item: item.edge_id)
        ]
        outgoing_states = [
            self._edge_state(context, edge)
            for edge in sorted(outgoing, key=lambda item: item.edge_id)
        ]
        required_incoming = [
            item.edge_id for item in incoming
            if item.required
        ]
        optional_incoming = [
            item.edge_id for item in incoming
            if not item.required
        ]
        outgoing_demands = [
            state.demand_id
            for state in outgoing_states
            if state.demand_id is not None
        ]

        neighborhood = SemanticTopologyNeighborhood(
            neighborhood_id="pending",
            semantic_graph_id=graph.semantic_graph_id,
            semantic_graph_authority_sha256=graph.authority_sha256,
            work_unit_id=work_unit_id,
            incoming_edges=incoming_states,
            outgoing_edges=outgoing_states,
            fan_in_count=len(incoming),
            fan_out_count=len(outgoing),
            required_incoming_edge_ids=sorted(required_incoming),
            optional_incoming_edge_ids=sorted(optional_incoming),
            outgoing_demand_ids=sorted(outgoing_demands),
            authority_sha256="pending",
        )
        sha = self.topology_authority.compute_neighborhood_sha256(
            neighborhood
        )
        neighborhood.authority_sha256 = sha
        neighborhood.neighborhood_id = (
            f"semantic_topology_neighborhood_{sha[:24]}"
        )
        return neighborhood

    def evaluate_join(
        self,
        *,
        run: Any,
        consumer_work_unit_id: str,
    ) -> SemanticJoinEvaluationResult:
        context, reason = self._context(run)
        if reason or context is None:
            return SemanticJoinEvaluationResult(
                status="insufficient_contract_evidence",
                reason_codes=[reason or "SEMANTIC_NWAY_CONTEXT_REQUIRED"],
            )
        graph = context["graph"]
        if consumer_work_unit_id not in context["work_units"]:
            return SemanticJoinEvaluationResult(
                status="insufficient_contract_evidence",
                reason_codes=["SEMANTIC_NWAY_CONSUMER_UNKNOWN"],
            )

        incoming = [
            edge for edge in graph.edges
            if edge.consumer_work_unit_id == consumer_work_unit_id
        ]
        if not incoming:
            return SemanticJoinEvaluationResult(
                status="not_applicable",
                reason_codes=["SEMANTIC_NWAY_JOIN_HAS_NO_INCOMING_EDGES"],
            )

        required = sorted(
            [edge for edge in incoming if edge.required],
            key=lambda item: item.edge_id,
        )
        optional = sorted(
            [edge for edge in incoming if not edge.required],
            key=lambda item: item.edge_id,
        )

        admitted: list[str] = []
        constrained: list[str] = []
        blocked: list[str] = []
        unresolved: list[str] = []
        optional_nonadmitted: list[str] = []
        compatibility_ids: list[str] = []
        effective_constraints: list[str] = []
        disclosures: list[str] = []

        for edge in required:
            compatibility, comp_reason = self._compatibility_for_edge(
                context,
                edge.edge_id,
            )
            if comp_reason:
                return SemanticJoinEvaluationResult(
                    status="insufficient_contract_evidence",
                    reason_codes=[comp_reason],
                )
            if compatibility is None:
                unresolved.append(edge.edge_id)
                continue
            compatibility_ids.append(compatibility.compatibility_id)
            if compatibility.decision == "blocked":
                blocked.append(edge.edge_id)
            elif compatibility.decision == "insufficient_evidence":
                unresolved.append(edge.edge_id)
            elif compatibility.decision == "admitted_with_constraints":
                constrained.append(edge.edge_id)
                effective_constraints.extend(
                    compatibility.effective_constraints
                )
                disclosures.extend(compatibility.disclosures)
            elif compatibility.decision == "admitted":
                admitted.append(edge.edge_id)
            else:
                unresolved.append(edge.edge_id)

        for edge in optional:
            compatibility, comp_reason = self._compatibility_for_edge(
                context,
                edge.edge_id,
            )
            if comp_reason:
                return SemanticJoinEvaluationResult(
                    status="insufficient_contract_evidence",
                    reason_codes=[comp_reason],
                )
            if compatibility is None:
                optional_nonadmitted.append(edge.edge_id)
                continue
            compatibility_ids.append(compatibility.compatibility_id)
            if compatibility.decision not in {
                "admitted",
                "admitted_with_constraints",
            }:
                optional_nonadmitted.append(edge.edge_id)

        if blocked:
            decision = "blocked"
            reason_codes = ["SEMANTIC_NWAY_REQUIRED_EDGE_BLOCKED"]
        elif unresolved:
            decision = "insufficient_evidence"
            reason_codes = ["SEMANTIC_NWAY_REQUIRED_EDGE_UNRESOLVED"]
        elif constrained:
            decision = "admitted_with_constraints"
            reason_codes = [
                "SEMANTIC_NWAY_REQUIRED_EDGES_ADMITTED_WITH_CONSTRAINTS"
            ]
        else:
            decision = "admitted"
            reason_codes = ["SEMANTIC_NWAY_REQUIRED_EDGES_ADMITTED"]

        join = SemanticJoinEvaluation(
            join_id="pending",
            semantic_graph_id=graph.semantic_graph_id,
            semantic_graph_authority_sha256=graph.authority_sha256,
            consumer_work_unit_id=consumer_work_unit_id,
            required_edge_ids=[edge.edge_id for edge in required],
            optional_edge_ids=[edge.edge_id for edge in optional],
            compatibility_ids=sorted(compatibility_ids),
            decision=decision,
            admitted_edge_ids=sorted(admitted),
            constrained_edge_ids=sorted(constrained),
            blocked_edge_ids=sorted(blocked),
            unresolved_edge_ids=sorted(unresolved),
            optional_nonadmitted_edge_ids=sorted(
                optional_nonadmitted
            ),
            effective_constraints=self._unique(
                effective_constraints
            ),
            disclosures=self._unique(disclosures),
            reason_codes=reason_codes,
            authority_sha256="pending",
        )
        sha = self.topology_authority.compute_join_sha256(join)
        join.authority_sha256 = sha
        join.join_id = f"semantic_join_{sha[:24]}"
        return SemanticJoinEvaluationResult(
            status="evaluated",
            join=join,
        )

    def _context(
        self,
        run: Any,
    ) -> tuple[dict[str, Any] | None, str | None]:
        plan = getattr(run, "plan", None)
        graph = getattr(plan, "semantic_execution_graph", None)
        if graph is None:
            return None, "SEMANTIC_NWAY_GRAPH_REQUIRED"
        if not self.graph_authority.verify(graph):
            return None, "SEMANTIC_NWAY_GRAPH_AUTHORITY_INVALID"

        demands = list(getattr(plan, "edge_semantic_demands", []) or [])
        offers = list(getattr(plan, "semantic_offers", []) or [])
        compatibilities = list(
            getattr(plan, "offer_demand_compatibilities", []) or []
        )
        graph_edges = {edge.edge_id: edge for edge in graph.edges}
        graph_units = {
            unit.work_unit_id: unit
            for unit in graph.work_units
        }

        demands_by_edge: dict[str, Any] = {}
        for demand in demands:
            if not self.demand_authority.verify(demand):
                return None, "SEMANTIC_NWAY_DEMAND_AUTHORITY_INVALID"
            if (
                demand.semantic_graph_id != graph.semantic_graph_id
                or demand.semantic_graph_authority_sha256
                != graph.authority_sha256
            ):
                return None, "SEMANTIC_NWAY_DEMAND_GRAPH_BINDING_MISMATCH"
            graph_edge = graph_edges.get(demand.edge_id)
            if graph_edge is None:
                return None, "SEMANTIC_NWAY_DEMAND_EDGE_UNKNOWN"
            if (
                demand.producer_work_unit_id
                != graph_edge.producer_work_unit_id
                or demand.consumer_work_unit_id
                != graph_edge.consumer_work_unit_id
            ):
                return None, "SEMANTIC_NWAY_DEMAND_EDGE_BINDING_MISMATCH"
            if demand.edge_id in demands_by_edge:
                return None, "SEMANTIC_NWAY_DUPLICATE_EDGE_DEMAND"
            demands_by_edge[demand.edge_id] = demand

        offers_by_unit: dict[str, Any] = {}
        offers_by_id: dict[str, Any] = {}
        for offer in offers:
            if not self.offer_authority.verify(offer):
                return None, "SEMANTIC_NWAY_OFFER_AUTHORITY_INVALID"
            if (
                offer.semantic_graph_id != graph.semantic_graph_id
                or offer.semantic_graph_authority_sha256
                != graph.authority_sha256
            ):
                return None, "SEMANTIC_NWAY_OFFER_GRAPH_BINDING_MISMATCH"
            if offer.producer_work_unit_id not in graph_units:
                return None, "SEMANTIC_NWAY_OFFER_WORK_UNIT_UNKNOWN"
            if offer.producer_work_unit_id in offers_by_unit:
                return None, "SEMANTIC_NWAY_DUPLICATE_WORK_UNIT_OFFER"
            offers_by_unit[offer.producer_work_unit_id] = offer
            offers_by_id[offer.offer_id] = offer

        compatibilities_by_edge: dict[str, Any] = {}
        for compatibility in compatibilities:
            if not self.compatibility_authority.verify(compatibility):
                return None, "SEMANTIC_NWAY_COMPATIBILITY_AUTHORITY_INVALID"
            if (
                compatibility.semantic_graph_id != graph.semantic_graph_id
                or compatibility.semantic_graph_authority_sha256
                != graph.authority_sha256
            ):
                return None, "SEMANTIC_NWAY_COMPATIBILITY_GRAPH_BINDING_MISMATCH"
            graph_edge = graph_edges.get(compatibility.edge_id)
            if graph_edge is None:
                return None, "SEMANTIC_NWAY_COMPATIBILITY_EDGE_UNKNOWN"
            if (
                compatibility.producer_work_unit_id
                != graph_edge.producer_work_unit_id
                or compatibility.consumer_work_unit_id
                != graph_edge.consumer_work_unit_id
            ):
                return None, "SEMANTIC_NWAY_COMPATIBILITY_EDGE_BINDING_MISMATCH"
            if compatibility.edge_id in compatibilities_by_edge:
                return None, "SEMANTIC_NWAY_DUPLICATE_EDGE_COMPATIBILITY"
            demand = next(
                (
                    item
                    for item in demands
                    if item.demand_id == compatibility.demand_id
                ),
                None,
            )
            offer = offers_by_id.get(compatibility.offer_id)
            if demand is None or offer is None:
                return None, "SEMANTIC_NWAY_COMPATIBILITY_INPUT_MISSING"
            if (
                compatibility.demand_authority_sha256
                != demand.authority_sha256
                or compatibility.offer_authority_sha256
                != offer.authority_sha256
            ):
                return None, "SEMANTIC_NWAY_COMPATIBILITY_INPUT_HASH_MISMATCH"
            compatibilities_by_edge[compatibility.edge_id] = compatibility

        return {
            "plan": plan,
            "graph": graph,
            "work_units": {
                unit.work_unit_id: unit
                for unit in graph.work_units
            },
            "demands_by_edge": demands_by_edge,
            "offers_by_unit": offers_by_unit,
            "compatibilities_by_edge": compatibilities_by_edge,
        }, None

    def _edge_state(
        self,
        context: dict[str, Any],
        edge: Any,
    ) -> SemanticTopologyEdgeState:
        demand = context["demands_by_edge"].get(edge.edge_id)
        offer = context["offers_by_unit"].get(
            edge.producer_work_unit_id
        )
        compatibility = context["compatibilities_by_edge"].get(
            edge.edge_id
        )
        return SemanticTopologyEdgeState(
            edge_id=edge.edge_id,
            producer_work_unit_id=edge.producer_work_unit_id,
            consumer_work_unit_id=edge.consumer_work_unit_id,
            required=edge.required,
            demand_id=demand.demand_id if demand is not None else None,
            demand_authority_sha256=(
                demand.authority_sha256
                if demand is not None
                else None
            ),
            offer_id=offer.offer_id if offer is not None else None,
            offer_authority_sha256=(
                offer.authority_sha256
                if offer is not None
                else None
            ),
            compatibility_id=(
                compatibility.compatibility_id
                if compatibility is not None
                else None
            ),
            compatibility_authority_sha256=(
                compatibility.authority_sha256
                if compatibility is not None
                else None
            ),
            compatibility_decision=(
                compatibility.decision
                if compatibility is not None
                else None
            ),
        )

    def _compatibility_for_edge(
        self,
        context: dict[str, Any],
        edge_id: str,
    ) -> tuple[Any | None, str | None]:
        compatibility = context["compatibilities_by_edge"].get(
            edge_id
        )
        return compatibility, None

    def _unique(self, values: list[str]) -> list[str]:
        return list(
            dict.fromkeys(
                str(item)
                for item in values
                if str(item).strip()
            )
        )
