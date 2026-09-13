from __future__ import annotations

from types import SimpleNamespace

from aipinho.schemas.runtime.execution_plan import (
    CanonicalExecutionPlan,
    CanonicalExecutionStep,
)
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.schemas.semantics.semantic_execution_graph import (
    SemanticDependencyEdgeCandidate,
    SemanticWorkDecompositionCandidate,
    SemanticWorkUnitCandidate,
)
from aipinho.schemas.semantics.semantic_offer import (
    ObservedWorkUnitSemanticOutcome,
)
from aipinho.services.semantics.edge_semantic_demand_compiler_service import (
    EdgeSemanticDemandCompilerService,
)
from aipinho.services.semantics.edge_semantic_demand_authority_service import (
    EdgeSemanticDemandAuthorityService,
)
from aipinho.services.semantics.offer_demand_compatibility_service import (
    OfferDemandCompatibilityService,
)
from aipinho.services.semantics.semantic_execution_graph_compiler_service import (
    SemanticExecutionGraphCompilerService,
)
from aipinho.services.semantics.semantic_nway_topology_authority_service import (
    SemanticNWayTopologyAuthorityService,
)
from aipinho.services.semantics.semantic_nway_topology_service import (
    SemanticNWayTopologyService,
)
from aipinho.services.semantics.semantic_offer_compiler_service import (
    SemanticOfferCompilerService,
)
from aipinho.services.semantics.semantic_nway_projection_service import (
    SemanticNWayProjectionService,
)
from aipinho.services.semantics.semantic_result_projection_service import (
    SemanticResultProjectionService,
)
from aipinho.services.semantics.task_semantic_vocabulary_compiler_service import (
    TaskSemanticVocabularyCompilerService,
)


def _run(*, second_join_required: bool = True):
    steps = [
        CanonicalExecutionStep(
            step_id="producer_a",
            step_type="observe",
            action="observe_a",
            required_capabilities=["read_workspace"],
            metadata={"work_modes": ["observation"]},
        ),
        CanonicalExecutionStep(
            step_id="producer_b",
            step_type="observe",
            action="observe_b",
            required_capabilities=["read_workspace"],
            metadata={"work_modes": ["observation"]},
        ),
        CanonicalExecutionStep(
            step_id="join_consumer",
            step_type="analyze",
            action="join_analysis",
            required_capabilities=["analysis"],
            metadata={
                "work_modes": ["analysis"],
                "required_use_safety": {"safe_for_catalog": [True]},
                "required_evidence_domains": ["identity_evidence"],
                "evidence_required": True,
            },
        ),
        CanonicalExecutionStep(
            step_id="planning_consumer",
            step_type="plan",
            action="planning",
            required_capabilities=["planning"],
            metadata={
                "work_modes": ["planning"],
                "required_use_safety": {"safe_for_planning": [True]},
                "required_evidence_domains": ["structure_evidence"],
                "evidence_required": True,
            },
        ),
    ]
    canonical = CanonicalExecutionPlan(
        semantic_goal="evaluate generic fan-in and fan-out",
        operation_kind="generic_nway",
        execution_steps=steps,
        required_capabilities=["read_workspace", "analysis", "planning"],
        rollback_strategy={"required": False},
        trace_id="trace_nway",
        metadata={"semantic_intent_graph": {"knowledge_output": True}},
    )
    plan = TaskRunPlan(
        plan_id="plan_nway",
        contract_type="generic_nway",
        canonical_execution_plan=canonical,
    )
    run = SimpleNamespace(
        run_id="task_run_nway",
        task_id="task_nway",
        plan=plan,
        intent_map={},
        capabilities_required=list(canonical.required_capabilities),
    )
    vocabulary = TaskSemanticVocabularyCompilerService().compile_for_run(run=run)
    assert vocabulary.status == "compiled"
    assert vocabulary.vocabulary is not None
    plan.task_semantic_vocabulary = vocabulary.vocabulary

    graph_result = SemanticExecutionGraphCompilerService().compile_candidate_for_run(
        run=run,
        candidate=SemanticWorkDecompositionCandidate(
            work_units=[
                SemanticWorkUnitCandidate(
                    unit_key="producer_a",
                    source_step_ids=["producer_a"],
                    semantic_goal="observe A",
                    work_modes=["observation"],
                    required_capabilities=["read_workspace"],
                ),
                SemanticWorkUnitCandidate(
                    unit_key="producer_b",
                    source_step_ids=["producer_b"],
                    semantic_goal="observe B",
                    work_modes=["observation"],
                    required_capabilities=["read_workspace"],
                ),
                SemanticWorkUnitCandidate(
                    unit_key="join",
                    source_step_ids=["join_consumer"],
                    semantic_goal="join producer evidence",
                    work_modes=["analysis"],
                    required_capabilities=["analysis"],
                ),
                SemanticWorkUnitCandidate(
                    unit_key="planning",
                    source_step_ids=["planning_consumer"],
                    semantic_goal="plan from producer A",
                    work_modes=["planning"],
                    required_capabilities=["planning"],
                ),
            ],
            edges=[
                SemanticDependencyEdgeCandidate(
                    producer_unit_key="producer_a",
                    consumer_unit_key="join",
                    relation="evidence_dependency",
                    required=True,
                ),
                SemanticDependencyEdgeCandidate(
                    producer_unit_key="producer_b",
                    consumer_unit_key="join",
                    relation="evidence_dependency",
                    required=second_join_required,
                ),
                SemanticDependencyEdgeCandidate(
                    producer_unit_key="producer_a",
                    consumer_unit_key="planning",
                    relation="evidence_dependency",
                    required=True,
                ),
            ],
            confidence=0.95,
            rationale="Two producers feed one join; producer A also fans out.",
        ),
    )
    assert graph_result.status == "accepted"
    assert graph_result.graph is not None
    plan.semantic_execution_graph = graph_result.graph

    demand_compiler = EdgeSemanticDemandCompilerService()
    plan.edge_semantic_demands = []
    for edge in graph_result.graph.edges:
        compiled = demand_compiler.compile_for_edge(run=run, edge_id=edge.edge_id)
        assert compiled.status == "compiled"
        assert compiled.demand is not None
        plan.edge_semantic_demands.append(compiled.demand)
    return run


def _unit(run, step_id: str):
    return next(
        unit
        for unit in run.plan.semantic_execution_graph.work_units
        if step_id in unit.source_step_ids
    )


def _compile_offer(
    run,
    *,
    step_id: str,
    catalog_safe: bool | None,
    planning_safe: bool | None = None,
    limitations=None,
    risk_constraints=None,
):
    unit = _unit(run, step_id)
    safety = {}
    if catalog_safe is not None:
        safety["safe_for_catalog"] = catalog_safe
    if planning_safe is not None:
        safety["safe_for_planning"] = planning_safe
    observed = ObservedWorkUnitSemanticOutcome(
        producer_work_unit_id=unit.work_unit_id,
        source_step_ids=list(unit.source_step_ids),
        result_status="completed_with_limitations" if limitations else "completed",
        result_ref=f"task_run_result:fixture#{step_id}",
        observed_use_safety=safety,
        evidence_domains=["identity_evidence", "structure_evidence"],
        evidence_refs=[f"evidence:{step_id}"],
        limitations=list(limitations or []),
        required_disclosures=(
            [f"{step_id}_has_limitations"] if limitations else []
        ),
        risk_constraints=list(risk_constraints or []),
        provenance={"source": "nway_fixture", "step_id": step_id},
    )
    result = SemanticOfferCompilerService().compile_for_work_unit(
        run=run,
        observed=observed,
    )
    assert result.status == "compiled"
    assert result.offer is not None
    return result.offer


def _materialize_compatibilities(run, offers):
    run.plan.semantic_offers = list(offers)
    service = OfferDemandCompatibilityService()
    run.plan.offer_demand_compatibilities = []
    by_unit = {offer.producer_work_unit_id: offer for offer in offers}
    for demand in run.plan.edge_semantic_demands:
        offer = by_unit[demand.producer_work_unit_id]
        result = service.evaluate(run=run, offer=offer, demand=demand)
        assert result.status == "evaluated"
        assert result.compatibility is not None
        run.plan.offer_demand_compatibilities.append(result.compatibility)


def test_neighborhood_represents_fan_in_and_fan_out_without_position_semantics() -> None:
    run = _run()
    offer_a = _compile_offer(
        run,
        step_id="producer_a",
        catalog_safe=True,
        planning_safe=False,
    )
    offer_b = _compile_offer(
        run,
        step_id="producer_b",
        catalog_safe=True,
    )
    _materialize_compatibilities(run, [offer_a, offer_b])

    service = SemanticNWayTopologyService()
    producer_a = _unit(run, "producer_a")
    join = _unit(run, "join_consumer")
    producer_neighborhood = service.neighborhood(
        run=run,
        work_unit_id=producer_a.work_unit_id,
    )
    join_neighborhood = service.neighborhood(
        run=run,
        work_unit_id=join.work_unit_id,
    )

    assert producer_neighborhood is not None
    assert join_neighborhood is not None
    assert producer_neighborhood.fan_out_count == 2
    assert producer_neighborhood.fan_in_count == 0
    assert join_neighborhood.fan_in_count == 2
    assert join_neighborhood.fan_out_count == 0
    assert len(producer_neighborhood.outgoing_demand_ids) == 2
    authority = SemanticNWayTopologyAuthorityService()
    assert authority.verify_neighborhood(producer_neighborhood)
    assert authority.verify_neighborhood(join_neighborhood)


def test_join_admits_when_all_required_incoming_edges_are_admitted() -> None:
    run = _run()
    offer_a = _compile_offer(
        run,
        step_id="producer_a",
        catalog_safe=True,
        planning_safe=False,
    )
    offer_b = _compile_offer(
        run,
        step_id="producer_b",
        catalog_safe=True,
    )
    _materialize_compatibilities(run, [offer_a, offer_b])

    join = _unit(run, "join_consumer")
    result = SemanticNWayTopologyService().evaluate_join(
        run=run,
        consumer_work_unit_id=join.work_unit_id,
    )

    assert result.status == "evaluated"
    assert result.join is not None
    assert result.join.decision == "admitted"
    assert len(result.join.required_edge_ids) == 2
    assert len(result.join.admitted_edge_ids) == 2
    assert SemanticNWayTopologyAuthorityService().verify_join(result.join)


def test_join_blocks_when_any_required_edge_is_blocked() -> None:
    run = _run()
    offer_a = _compile_offer(
        run,
        step_id="producer_a",
        catalog_safe=True,
        planning_safe=False,
    )
    offer_b = _compile_offer(
        run,
        step_id="producer_b",
        catalog_safe=False,
    )
    _materialize_compatibilities(run, [offer_a, offer_b])

    join = _unit(run, "join_consumer")
    result = SemanticNWayTopologyService().evaluate_join(
        run=run,
        consumer_work_unit_id=join.work_unit_id,
    )

    assert result.join is not None
    assert result.join.decision == "blocked"
    assert len(result.join.blocked_edge_ids) == 1


def test_optional_blocked_edge_does_not_block_required_join() -> None:
    run = _run(second_join_required=False)
    offer_a = _compile_offer(
        run,
        step_id="producer_a",
        catalog_safe=True,
        planning_safe=False,
    )
    offer_b = _compile_offer(
        run,
        step_id="producer_b",
        catalog_safe=False,
    )
    _materialize_compatibilities(run, [offer_a, offer_b])

    join = _unit(run, "join_consumer")
    result = SemanticNWayTopologyService().evaluate_join(
        run=run,
        consumer_work_unit_id=join.work_unit_id,
    )

    assert result.join is not None
    assert result.join.decision == "admitted"
    assert len(result.join.required_edge_ids) == 1
    assert len(result.join.optional_edge_ids) == 1
    assert len(result.join.optional_nonadmitted_edge_ids) == 1


def test_missing_required_compatibility_is_insufficient_evidence() -> None:
    run = _run()
    offer_a = _compile_offer(
        run,
        step_id="producer_a",
        catalog_safe=True,
        planning_safe=False,
    )
    offer_b = _compile_offer(
        run,
        step_id="producer_b",
        catalog_safe=True,
    )
    _materialize_compatibilities(run, [offer_a, offer_b])
    join = _unit(run, "join_consumer")
    incoming = [
        edge
        for edge in run.plan.semantic_execution_graph.edges
        if edge.consumer_work_unit_id == join.work_unit_id
    ]
    removed_edge_id = incoming[0].edge_id
    run.plan.offer_demand_compatibilities = [
        item
        for item in run.plan.offer_demand_compatibilities
        if item.edge_id != removed_edge_id
    ]

    result = SemanticNWayTopologyService().evaluate_join(
        run=run,
        consumer_work_unit_id=join.work_unit_id,
    )

    assert result.join is not None
    assert result.join.decision == "insufficient_evidence"
    assert removed_edge_id in result.join.unresolved_edge_ids


def test_join_combines_required_constraints_and_disclosures() -> None:
    run = _run()
    offer_a = _compile_offer(
        run,
        step_id="producer_a",
        catalog_safe=True,
        planning_safe=True,
        limitations=["scope_limited"],
        risk_constraints=["restrict_scope"],
    )
    offer_b = _compile_offer(
        run,
        step_id="producer_b",
        catalog_safe=True,
    )
    _materialize_compatibilities(run, [offer_a, offer_b])

    join = _unit(run, "join_consumer")
    result = SemanticNWayTopologyService().evaluate_join(
        run=run,
        consumer_work_unit_id=join.work_unit_id,
    )

    assert result.join is not None
    assert result.join.decision == "admitted_with_constraints"
    assert "restrict_scope" in result.join.effective_constraints
    assert "producer_a_has_limitations" in result.join.disclosures
    assert len(result.join.constrained_edge_ids) == 1


def test_nway_projection_persists_all_neighborhoods_and_incoming_joins() -> None:
    run = _run()
    offer_a = _compile_offer(
        run,
        step_id="producer_a",
        catalog_safe=True,
        planning_safe=True,
    )
    offer_b = _compile_offer(
        run,
        step_id="producer_b",
        catalog_safe=True,
    )
    _materialize_compatibilities(run, [offer_a, offer_b])

    projection = SemanticNWayProjectionService().project(run=run)

    assert projection["status"] == "projected"
    assert projection["neighborhoods_projected"] == 4
    assert projection["joins_evaluated"] == 2
    assert len(run.plan.semantic_topology_neighborhoods) == 4
    assert len(run.plan.semantic_join_evaluations) == 2
    assert run.plan.metadata["semantic_nway_projection"][
        "neighborhoods_projected"
    ] == 4
    assert {
        item.consumer_work_unit_id
        for item in run.plan.semantic_join_evaluations
    } == {
        _unit(run, "join_consumer").work_unit_id,
        _unit(run, "planning_consumer").work_unit_id,
    }


def test_terminal_semantic_result_projection_includes_nway_views() -> None:
    run = _run()
    result = TaskRunResult(
        run_id=run.run_id,
        status="completed",
        summary="completed",
        step_summaries=[
            {
                "step_id": "producer_a",
                "step_type": "observe",
                "status": "completed",
                "output_summary": {
                    "semantic_outcome": {
                        "use_safety": {
                            "safe_for_catalog": True,
                            "safe_for_planning": True,
                        },
                        "evidence_domains": [
                            "identity_evidence",
                            "structure_evidence",
                        ],
                        "evidence_refs": ["evidence:producer_a"],
                    }
                },
                "warnings": [],
                "violations": [],
            },
            {
                "step_id": "producer_b",
                "step_type": "observe",
                "status": "completed",
                "output_summary": {
                    "semantic_outcome": {
                        "use_safety": {"safe_for_catalog": True},
                        "evidence_domains": ["identity_evidence"],
                        "evidence_refs": ["evidence:producer_b"],
                    }
                },
                "warnings": [],
                "violations": [],
            },
            {
                "step_id": "join_consumer",
                "step_type": "analyze",
                "status": "completed",
                "output_summary": {},
                "warnings": [],
                "violations": [],
            },
            {
                "step_id": "planning_consumer",
                "step_type": "plan",
                "status": "completed",
                "output_summary": {},
                "warnings": [],
                "violations": [],
            },
        ],
    )

    projection = SemanticResultProjectionService().project(
        run=run,
        result=result,
    )

    assert projection["status"] == "projected"
    assert projection["nway_projection"]["status"] == "projected"
    assert projection["nway_projection"]["neighborhoods_projected"] == 4
    assert projection["nway_projection"]["joins_evaluated"] == 2
    decisions = {
        item.consumer_work_unit_id: item.decision
        for item in run.plan.semantic_join_evaluations
    }
    assert decisions[_unit(run, "join_consumer").work_unit_id] == "admitted"
    assert decisions[_unit(run, "planning_consumer").work_unit_id] == "admitted"


def test_valid_demand_from_another_graph_is_rejected() -> None:
    run = _run()
    offer_a = _compile_offer(
        run,
        step_id="producer_a",
        catalog_safe=True,
        planning_safe=True,
    )
    offer_b = _compile_offer(
        run,
        step_id="producer_b",
        catalog_safe=True,
    )
    _materialize_compatibilities(run, [offer_a, offer_b])

    demand = run.plan.edge_semantic_demands[0]
    demand.semantic_graph_id = "semantic_execution_graph_foreign"
    authority = EdgeSemanticDemandAuthorityService()
    demand.authority_sha256 = authority.compute_authority_sha256(demand)

    join = _unit(run, "join_consumer")
    result = SemanticNWayTopologyService().evaluate_join(
        run=run,
        consumer_work_unit_id=join.work_unit_id,
    )

    assert result.status == "insufficient_contract_evidence"
    assert result.reason_codes == [
        "SEMANTIC_NWAY_DEMAND_GRAPH_BINDING_MISMATCH"
    ]
