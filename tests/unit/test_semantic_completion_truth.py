from __future__ import annotations

from types import SimpleNamespace

from aipinho.services.semantics.semantic_completion_truth_service import (
    SemanticCompletionTruthService,
)
from aipinho.services.semantics.semantic_truth_facet_authority_service import (
    SemanticTruthFacetAuthorityService,
)


class _Authority:
    def verify(self, value) -> bool:
        return not bool(getattr(value, "invalid_authority", False))


class _NWayAuthority:
    def verify_join(self, value) -> bool:
        return not bool(getattr(value, "invalid_authority", False))


def _edge(
    edge_id: str,
    *,
    producer: str,
    consumer: str,
    required: bool = True,
):
    return SimpleNamespace(
        edge_id=edge_id,
        producer_work_unit_id=producer,
        consumer_work_unit_id=consumer,
        required=required,
    )


def _demand(
    edge,
    *,
    graph_id: str,
    graph_sha: str,
    status: str = "ready",
    demand_id: str | None = None,
):
    return SimpleNamespace(
        demand_id=demand_id or f"demand_{edge.edge_id}",
        edge_id=edge.edge_id,
        semantic_graph_id=graph_id,
        semantic_graph_authority_sha256=graph_sha,
        producer_work_unit_id=edge.producer_work_unit_id,
        consumer_work_unit_id=edge.consumer_work_unit_id,
        status=status,
        authority_sha256=f"demand_sha_{edge.edge_id}",
    )


def _offer(
    producer: str,
    *,
    graph_id: str,
    graph_sha: str,
    offer_id: str | None = None,
):
    return SimpleNamespace(
        offer_id=offer_id or f"offer_{producer}",
        producer_work_unit_id=producer,
        semantic_graph_id=graph_id,
        semantic_graph_authority_sha256=graph_sha,
        authority_sha256=f"offer_sha_{producer}",
    )


def _compatibility(
    edge,
    *,
    graph_id: str,
    graph_sha: str,
    demand,
    offer,
    decision: str = "admitted",
    disclosures=None,
    constraints=None,
):
    return SimpleNamespace(
        compatibility_id=f"compat_{edge.edge_id}",
        edge_id=edge.edge_id,
        semantic_graph_id=graph_id,
        semantic_graph_authority_sha256=graph_sha,
        producer_work_unit_id=edge.producer_work_unit_id,
        consumer_work_unit_id=edge.consumer_work_unit_id,
        demand_id=demand.demand_id,
        demand_authority_sha256=demand.authority_sha256,
        offer_id=offer.offer_id,
        offer_authority_sha256=offer.authority_sha256,
        decision=decision,
        disclosures=list(disclosures or []),
        effective_constraints=list(constraints or []),
        authority_sha256=f"compat_sha_{edge.edge_id}",
    )


def _join(
    *,
    consumer: str,
    graph_id: str,
    graph_sha: str,
    required_edge_ids: list[str],
    decision: str = "admitted",
    disclosures=None,
    constraints=None,
):
    return SimpleNamespace(
        join_id=f"join_{consumer}",
        consumer_work_unit_id=consumer,
        semantic_graph_id=graph_id,
        semantic_graph_authority_sha256=graph_sha,
        required_edge_ids=list(required_edge_ids),
        decision=decision,
        disclosures=list(disclosures or []),
        effective_constraints=list(constraints or []),
        authority_sha256=f"join_sha_{consumer}",
    )


def _run(
    *,
    edges,
    demands=None,
    offers=None,
    compatibilities=None,
    joins=None,
    metadata=None,
):
    graph_id = "semantic_graph_fixture"
    graph_sha = "graph_sha_fixture"
    graph = SimpleNamespace(
        semantic_graph_id=graph_id,
        authority_sha256=graph_sha,
        edges=list(edges),
    )
    plan = SimpleNamespace(
        semantic_execution_graph=graph,
        active_semantic_graph_revision_id=None,
        edge_semantic_demands=list(demands or []),
        semantic_offers=list(offers or []),
        offer_demand_compatibilities=list(compatibilities or []),
        semantic_join_evaluations=list(joins or []),
        metadata=dict(metadata or {}),
    )
    return SimpleNamespace(plan=plan), graph_id, graph_sha


def _service(**overrides):
    return SemanticCompletionTruthService(
        graph_authority=overrides.get("graph_authority", _Authority()),
        demand_authority=overrides.get("demand_authority", _Authority()),
        offer_authority=overrides.get("offer_authority", _Authority()),
        compatibility_authority=overrides.get(
            "compatibility_authority",
            _Authority(),
        ),
        nway_authority=overrides.get("nway_authority", _NWayAuthority()),
    )


def test_no_semantic_graph_is_not_applicable_and_non_blocking() -> None:
    run = SimpleNamespace(
        plan=SimpleNamespace(semantic_execution_graph=None)
    )

    facet = _service().evaluate(run)

    assert facet.status == "not_applicable"
    assert facet.safe_to_report_success is True
    assert SemanticTruthFacetAuthorityService().verify(facet)


def test_single_required_admitted_edge_is_ready() -> None:
    edge = _edge("edge_a", producer="producer_a", consumer="consumer_a")
    run, graph_id, graph_sha = _run(edges=[edge])
    demand = _demand(edge, graph_id=graph_id, graph_sha=graph_sha)
    offer = _offer(
        edge.producer_work_unit_id,
        graph_id=graph_id,
        graph_sha=graph_sha,
    )
    compatibility = _compatibility(
        edge,
        graph_id=graph_id,
        graph_sha=graph_sha,
        demand=demand,
        offer=offer,
    )
    run.plan.edge_semantic_demands = [demand]
    run.plan.semantic_offers = [offer]
    run.plan.offer_demand_compatibilities = [compatibility]

    facet = _service().evaluate(run)

    assert facet.status == "ready"
    assert facet.safe_to_report_success is True
    assert facet.admitted_edge_ids == ["edge_a"]
    assert facet.unresolved_edge_ids == []
    assert SemanticTruthFacetAuthorityService().verify(facet)


def test_admitted_with_constraints_requires_disclosure_and_is_not_safe() -> None:
    edge = _edge("edge_a", producer="producer_a", consumer="consumer_a")
    run, graph_id, graph_sha = _run(edges=[edge])
    demand = _demand(edge, graph_id=graph_id, graph_sha=graph_sha)
    offer = _offer(
        edge.producer_work_unit_id,
        graph_id=graph_id,
        graph_sha=graph_sha,
    )
    compatibility = _compatibility(
        edge,
        graph_id=graph_id,
        graph_sha=graph_sha,
        demand=demand,
        offer=offer,
        decision="admitted_with_constraints",
        disclosures=["identity_scope_limited"],
        constraints=["restrict_scope"],
    )
    run.plan.edge_semantic_demands = [demand]
    run.plan.semantic_offers = [offer]
    run.plan.offer_demand_compatibilities = [compatibility]

    facet = _service().evaluate(run)

    assert facet.status == "constrained"
    assert facet.safe_to_report_success is False
    assert facet.constrained_edge_ids == ["edge_a"]
    assert set(facet.disclosures) == {
        "identity_scope_limited",
        "restrict_scope",
    }


def test_explicit_blocked_required_edge_blocks_semantic_truth() -> None:
    edge = _edge("edge_a", producer="producer_a", consumer="consumer_a")
    run, graph_id, graph_sha = _run(edges=[edge])
    demand = _demand(edge, graph_id=graph_id, graph_sha=graph_sha)
    offer = _offer(
        edge.producer_work_unit_id,
        graph_id=graph_id,
        graph_sha=graph_sha,
    )
    compatibility = _compatibility(
        edge,
        graph_id=graph_id,
        graph_sha=graph_sha,
        demand=demand,
        offer=offer,
        decision="blocked",
    )
    run.plan.edge_semantic_demands = [demand]
    run.plan.semantic_offers = [offer]
    run.plan.offer_demand_compatibilities = [compatibility]

    facet = _service().evaluate(run)

    assert facet.status == "blocked"
    assert facet.safe_to_report_success is False
    assert facet.blocked_edge_ids == ["edge_a"]


def test_missing_compatibility_is_insufficient_evidence_not_blocked() -> None:
    edge = _edge("edge_a", producer="producer_a", consumer="consumer_a")
    run, graph_id, graph_sha = _run(edges=[edge])
    demand = _demand(edge, graph_id=graph_id, graph_sha=graph_sha)
    run.plan.edge_semantic_demands = [demand]

    facet = _service().evaluate(run)

    assert facet.status == "insufficient_evidence"
    assert facet.safe_to_report_success is False
    assert facet.unresolved_edge_ids == ["edge_a"]
    assert facet.blocked_edge_ids == []


def test_partial_demand_is_insufficient_evidence() -> None:
    edge = _edge("edge_a", producer="producer_a", consumer="consumer_a")
    run, graph_id, graph_sha = _run(edges=[edge])
    run.plan.edge_semantic_demands = [
        _demand(
            edge,
            graph_id=graph_id,
            graph_sha=graph_sha,
            status="partial",
        )
    ]

    facet = _service().evaluate(run)

    assert facet.status == "insufficient_evidence"
    assert facet.partial_demand_edge_ids == ["edge_a"]
    assert facet.unresolved_edge_ids == ["edge_a"]


def test_required_fan_in_without_join_is_unresolved() -> None:
    edge_a = _edge(
        "edge_a",
        producer="producer_a",
        consumer="join_consumer",
    )
    edge_b = _edge(
        "edge_b",
        producer="producer_b",
        consumer="join_consumer",
    )
    run, graph_id, graph_sha = _run(edges=[edge_a, edge_b])
    demand_a = _demand(edge_a, graph_id=graph_id, graph_sha=graph_sha)
    demand_b = _demand(edge_b, graph_id=graph_id, graph_sha=graph_sha)
    offer_a = _offer("producer_a", graph_id=graph_id, graph_sha=graph_sha)
    offer_b = _offer("producer_b", graph_id=graph_id, graph_sha=graph_sha)
    run.plan.edge_semantic_demands = [demand_a, demand_b]
    run.plan.semantic_offers = [offer_a, offer_b]
    run.plan.offer_demand_compatibilities = [
        _compatibility(
            edge_a,
            graph_id=graph_id,
            graph_sha=graph_sha,
            demand=demand_a,
            offer=offer_a,
        ),
        _compatibility(
            edge_b,
            graph_id=graph_id,
            graph_sha=graph_sha,
            demand=demand_b,
            offer=offer_b,
        ),
    ]

    facet = _service().evaluate(run)

    assert facet.status == "insufficient_evidence"
    assert facet.required_join_consumer_ids == ["join_consumer"]
    assert facet.unresolved_join_consumer_ids == ["join_consumer"]


def test_required_fan_in_with_admitted_join_is_ready() -> None:
    edge_a = _edge(
        "edge_a",
        producer="producer_a",
        consumer="join_consumer",
    )
    edge_b = _edge(
        "edge_b",
        producer="producer_b",
        consumer="join_consumer",
    )
    run, graph_id, graph_sha = _run(edges=[edge_a, edge_b])
    demand_a = _demand(edge_a, graph_id=graph_id, graph_sha=graph_sha)
    demand_b = _demand(edge_b, graph_id=graph_id, graph_sha=graph_sha)
    offer_a = _offer("producer_a", graph_id=graph_id, graph_sha=graph_sha)
    offer_b = _offer("producer_b", graph_id=graph_id, graph_sha=graph_sha)
    run.plan.edge_semantic_demands = [demand_a, demand_b]
    run.plan.semantic_offers = [offer_a, offer_b]
    run.plan.offer_demand_compatibilities = [
        _compatibility(
            edge_a,
            graph_id=graph_id,
            graph_sha=graph_sha,
            demand=demand_a,
            offer=offer_a,
        ),
        _compatibility(
            edge_b,
            graph_id=graph_id,
            graph_sha=graph_sha,
            demand=demand_b,
            offer=offer_b,
        ),
    ]
    run.plan.semantic_join_evaluations = [
        _join(
            consumer="join_consumer",
            graph_id=graph_id,
            graph_sha=graph_sha,
            required_edge_ids=["edge_a", "edge_b"],
        )
    ]

    facet = _service().evaluate(run)

    assert facet.status == "ready"
    assert facet.safe_to_report_success is True


def test_revision_invalidated_projection_is_insufficient() -> None:
    edge = _edge("edge_a", producer="producer_a", consumer="consumer_a")
    run, _, _ = _run(
        edges=[edge],
        metadata={
            "semantic_result_projection": {
                "status": "invalidated_by_graph_revision"
            }
        },
    )

    facet = _service().evaluate(run)

    assert facet.status == "insufficient_evidence"
    assert facet.unresolved_edge_ids == ["edge_a"]
    assert facet.reason_codes == [
        "SEMANTIC_TRUTH_RESULT_PROJECTION_INVALIDATED"
    ]


def test_valid_demand_from_another_graph_is_rejected() -> None:
    edge = _edge("edge_a", producer="producer_a", consumer="consumer_a")
    run, graph_id, graph_sha = _run(edges=[edge])
    demand = _demand(
        edge,
        graph_id="foreign_graph",
        graph_sha=graph_sha,
    )
    run.plan.edge_semantic_demands = [demand]

    facet = _service().evaluate(run)

    assert facet.status == "blocked"
    assert facet.safe_to_report_success is False
    assert facet.reason_codes == [
        "SEMANTIC_TRUTH_CONTRACT_AUTHORITY_INVALID"
    ]
    assert facet.invalid_authority_refs == [
        f"demand_binding:{demand.demand_id}"
    ]
