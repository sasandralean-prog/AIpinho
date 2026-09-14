from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

from aipinho.schemas.runtime.execution_plan import (
    CanonicalExecutionPlan,
    CanonicalExecutionStep,
)
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.semantics.semantic_graph_revision import (
    SemanticGraphRevisionEdgeAddition,
    SemanticGraphRevisionProposal,
    SemanticGraphRevisionWorkUnitAddition,
)
from aipinho.schemas.semantics.semantic_offer import (
    ObservedWorkUnitSemanticOutcome,
)
from aipinho.services.semantics.edge_semantic_demand_compiler_service import (
    EdgeSemanticDemandCompilerService,
)
from aipinho.services.semantics.semantic_execution_graph_authority_service import (
    SemanticExecutionGraphAuthorityService,
)
from aipinho.services.semantics.semantic_execution_graph_compiler_service import (
    SemanticExecutionGraphCompilerService,
)
from aipinho.services.semantics.semantic_graph_revision_authority_service import (
    SemanticGraphRevisionAuthorityService,
)
from aipinho.services.semantics.semantic_graph_activation_service import (
    SemanticGraphActivationService,
)
from aipinho.services.semantics.semantic_offer_compiler_service import (
    SemanticOfferCompilerService,
)
from aipinho.services.semantics.offer_demand_compatibility_service import (
    OfferDemandCompatibilityService,
)
from aipinho.services.semantics.semantic_nway_projection_service import (
    SemanticNWayProjectionService,
)
from aipinho.services.semantics.semantic_graph_revision_service import (
    SemanticGraphRevisionService,
)
from aipinho.services.semantics.task_semantic_vocabulary_compiler_service import (
    TaskSemanticVocabularyCompilerService,
)


def _run():
    canonical = CanonicalExecutionPlan(
        semantic_goal="observe then analyze",
        operation_kind="generic_revision_fixture",
        execution_steps=[
            CanonicalExecutionStep(
                step_id="step_a",
                step_type="observe",
                action="observe",
                required_capabilities=["read_workspace"],
                metadata={"work_modes": ["observation"]},
            ),
            CanonicalExecutionStep(
                step_id="step_b",
                step_type="analyze",
                action="analyze",
                required_capabilities=["analysis"],
                depends_on=["step_a"],
                metadata={"work_modes": ["analysis"]},
            ),
        ],
        required_capabilities=["read_workspace", "analysis"],
        rollback_strategy={"required": False},
        trace_id="trace_revision_fixture",
        metadata={"semantic_intent_graph": {"knowledge_output": True}},
    )
    plan = TaskRunPlan(
        plan_id="plan_revision_fixture",
        contract_type="generic_revision_fixture",
        canonical_execution_plan=canonical,
    )
    run = SimpleNamespace(
        run_id="task_run_revision_fixture",
        task_id="task_revision_fixture",
        plan=plan,
        intent_map={},
        capabilities_required=list(canonical.required_capabilities),
    )
    vocabulary = TaskSemanticVocabularyCompilerService().compile_for_run(run=run)
    assert vocabulary.status == "compiled"
    assert vocabulary.vocabulary is not None
    plan.task_semantic_vocabulary = vocabulary.vocabulary

    graph = SemanticExecutionGraphCompilerService().compile_structural_for_run(
        run=run
    )
    assert graph.status == "accepted"
    assert graph.graph is not None
    assert graph.graph.status == "ready"
    plan.semantic_execution_graph = graph.graph

    demand_compiler = EdgeSemanticDemandCompilerService()
    plan.edge_semantic_demands = []
    for edge in graph.graph.edges:
        demand = demand_compiler.compile_for_edge(run=run, edge_id=edge.edge_id)
        assert demand.status == "compiled"
        assert demand.demand is not None
        plan.edge_semantic_demands.append(demand.demand)
    return run


def _proposal(run, **overrides):
    parent = run.plan.semantic_execution_graph
    payload = dict(
        parent_graph_id=parent.semantic_graph_id,
        parent_graph_authority_sha256=parent.authority_sha256,
        parent_revision_id=None,
        revision_number=1,
        reason="new evidence requires an explicit validation work unit",
        provenance={
            "source": "synthetic_discovery",
            "evidence_ref": "evidence:new_requirement",
        },
        add_work_units=[
            SemanticGraphRevisionWorkUnitAddition(
                addition_key="validation_unit",
                source_step_ids=["discovered_validation_step"],
                semantic_goal="validate newly discovered evidence",
                work_modes=["validation"],
                classification_status="explicit",
                required_capabilities=["analysis"],
            )
        ],
        add_edges=[],
    )
    payload.update(overrides)
    return SemanticGraphRevisionProposal(**payload)


def test_revision_creates_new_child_graph_and_preserves_parent() -> None:
    run = _run()
    parent = run.plan.semantic_execution_graph
    parent_before = deepcopy(parent.model_dump(mode="json"))
    demands_before = deepcopy(
        [item.model_dump(mode="json") for item in run.plan.edge_semantic_demands]
    )
    consumer = next(
        unit for unit in parent.work_units if "step_b" in unit.source_step_ids
    )
    proposal = _proposal(
        run,
        add_edges=[
            SemanticGraphRevisionEdgeAddition(
                addition_key="validation_to_analysis",
                producer_ref="addition:validation_unit",
                consumer_ref=consumer.work_unit_id,
                relation="validation_dependency",
                required=True,
                source_refs=["discovery:new_validation_requirement"],
            )
        ],
    )

    result = SemanticGraphRevisionService().apply(
        run=run,
        proposal=proposal,
    )

    assert result.status == "applied"
    assert result.child_graph is not None
    assert result.revision is not None
    child = result.child_graph
    revision = result.revision
    assert child.semantic_graph_id != parent.semantic_graph_id
    assert child.authority_sha256 != parent.authority_sha256
    assert len(child.work_units) == len(parent.work_units) + 1
    assert len(child.edges) == len(parent.edges) + 1
    assert SemanticExecutionGraphAuthorityService().verify(child)
    assert SemanticGraphRevisionAuthorityService().verify(revision)
    assert revision.parent_graph_id == parent.semantic_graph_id
    assert revision.parent_graph_authority_sha256 == parent.authority_sha256
    assert revision.child_graph_id == child.semantic_graph_id
    assert revision.child_graph_authority_sha256 == child.authority_sha256
    assert revision.edges_requiring_demand_recompile == sorted(
        edge.edge_id for edge in child.edges
    )
    assert parent.model_dump(mode="json") == parent_before
    assert [
        item.model_dump(mode="json")
        for item in run.plan.edge_semantic_demands
    ] == demands_before


def test_revision_is_deterministic_for_same_parent_and_intent() -> None:
    run = _run()
    proposal = _proposal(run)
    service = SemanticGraphRevisionService()

    first = service.apply(run=run, proposal=proposal)
    second = service.apply(run=run, proposal=proposal)

    assert first.status == "applied"
    assert second.status == "applied"
    assert first.child_graph is not None
    assert second.child_graph is not None
    assert first.revision is not None
    assert second.revision is not None
    assert first.child_graph.authority_sha256 == second.child_graph.authority_sha256
    assert first.revision.revision_intent_sha256 == (
        second.revision.revision_intent_sha256
    )
    assert first.revision.authority_sha256 == second.revision.authority_sha256


def test_revision_rejects_cycle() -> None:
    run = _run()
    graph = run.plan.semantic_execution_graph
    producer = next(
        unit for unit in graph.work_units if "step_a" in unit.source_step_ids
    )
    consumer = next(
        unit for unit in graph.work_units if "step_b" in unit.source_step_ids
    )
    proposal = _proposal(
        run,
        add_work_units=[],
        add_edges=[
            SemanticGraphRevisionEdgeAddition(
                addition_key="reverse_edge",
                producer_ref=consumer.work_unit_id,
                consumer_ref=producer.work_unit_id,
                relation="semantic_dependency",
                required=True,
            )
        ],
    )

    result = SemanticGraphRevisionService().apply(
        run=run,
        proposal=proposal,
    )

    assert result.status == "blocked"
    assert result.reason_codes == ["GRAPH_REVISION_CYCLE_DETECTED"]


def test_revision_requires_incident_edges_removed_before_work_unit_removal() -> None:
    run = _run()
    graph = run.plan.semantic_execution_graph
    consumer = next(
        unit for unit in graph.work_units if "step_b" in unit.source_step_ids
    )
    proposal = _proposal(
        run,
        add_work_units=[],
        remove_work_unit_ids=[consumer.work_unit_id],
    )

    result = SemanticGraphRevisionService().apply(
        run=run,
        proposal=proposal,
    )

    assert result.status == "blocked"
    assert result.reason_codes == [
        "GRAPH_REVISION_WORK_UNIT_HAS_UNREMOVED_EDGES"
    ]


def test_revision_can_remove_unit_when_incident_edges_are_explicitly_removed() -> None:
    run = _run()
    graph = run.plan.semantic_execution_graph
    consumer = next(
        unit for unit in graph.work_units if "step_b" in unit.source_step_ids
    )
    incident = [
        edge.edge_id
        for edge in graph.edges
        if edge.consumer_work_unit_id == consumer.work_unit_id
        or edge.producer_work_unit_id == consumer.work_unit_id
    ]
    proposal = _proposal(
        run,
        add_work_units=[],
        remove_work_unit_ids=[consumer.work_unit_id],
        remove_edge_ids=incident,
    )

    result = SemanticGraphRevisionService().apply(
        run=run,
        proposal=proposal,
    )

    assert result.status == "applied"
    assert result.child_graph is not None
    assert len(result.child_graph.work_units) == 1
    assert result.child_graph.edges == []
    assert result.revision is not None
    assert result.revision.removed_work_unit_ids == [consumer.work_unit_id]
    assert result.revision.removed_edge_ids == sorted(incident)


def test_revision_parent_hash_mismatch_fails_closed() -> None:
    run = _run()
    proposal = _proposal(
        run,
        parent_graph_authority_sha256="0" * 64,
    )

    result = SemanticGraphRevisionService().apply(
        run=run,
        proposal=proposal,
    )

    assert result.status == "blocked"
    assert result.reason_codes == ["GRAPH_REVISION_PARENT_BINDING_MISMATCH"]


def test_revision_rejects_duplicate_source_step_in_child_graph() -> None:
    run = _run()
    proposal = _proposal(
        run,
        add_work_units=[
            SemanticGraphRevisionWorkUnitAddition(
                addition_key="duplicate_step",
                source_step_ids=["step_a"],
                semantic_goal="invalid duplicate binding",
                work_modes=["validation"],
                classification_status="explicit",
                required_capabilities=["analysis"],
            )
        ],
    )

    result = SemanticGraphRevisionService().apply(
        run=run,
        proposal=proposal,
    )

    assert result.status == "blocked"
    assert result.reason_codes == ["GRAPH_REVISION_SOURCE_STEP_DUPLICATED"]


def _populate_parent_semantic_results(run) -> None:
    graph = run.plan.semantic_execution_graph
    producer = next(
        unit for unit in graph.work_units if "step_a" in unit.source_step_ids
    )
    observed = ObservedWorkUnitSemanticOutcome(
        producer_work_unit_id=producer.work_unit_id,
        source_step_ids=list(producer.source_step_ids),
        result_status="completed",
        result_ref="task_run_result:parent",
        observed_use_safety={"safe_for_catalog": True},
        evidence_refs=["evidence:parent"],
        provenance={"source": "revision_parent_fixture"},
    )
    compiled_offer = SemanticOfferCompilerService().compile_for_work_unit(
        run=run,
        observed=observed,
    )
    assert compiled_offer.status == "compiled"
    assert compiled_offer.offer is not None
    run.plan.semantic_offers = [compiled_offer.offer]

    demand = run.plan.edge_semantic_demands[0]
    evaluated = OfferDemandCompatibilityService().evaluate(
        run=run,
        offer=compiled_offer.offer,
        demand=demand,
    )
    assert evaluated.status == "evaluated"
    assert evaluated.compatibility is not None
    run.plan.offer_demand_compatibilities = [evaluated.compatibility]
    projection = SemanticNWayProjectionService().project(run=run)
    assert projection["status"] == "projected"


def test_activation_archives_parent_and_recompiles_child_demands() -> None:
    run = _run()
    _populate_parent_semantic_results(run)
    parent = deepcopy(run.plan.semantic_execution_graph)
    old_demands = deepcopy(run.plan.edge_semantic_demands)
    old_offers = deepcopy(run.plan.semantic_offers)
    old_compatibilities = deepcopy(run.plan.offer_demand_compatibilities)
    old_neighborhoods = deepcopy(run.plan.semantic_topology_neighborhoods)
    old_joins = deepcopy(run.plan.semantic_join_evaluations)

    consumer = next(
        unit
        for unit in parent.work_units
        if "step_b" in unit.source_step_ids
    )
    proposal = _proposal(
        run,
        add_edges=[
            SemanticGraphRevisionEdgeAddition(
                addition_key="validation_to_analysis",
                producer_ref="addition:validation_unit",
                consumer_ref=consumer.work_unit_id,
                relation="validation_dependency",
                required=True,
            )
        ],
    )
    application = SemanticGraphRevisionService().apply(
        run=run,
        proposal=proposal,
    )
    assert application.status == "applied"
    assert application.child_graph is not None
    assert application.revision is not None

    activation = SemanticGraphActivationService().activate(
        run=run,
        application=application,
    )

    assert activation.status == "activated"
    assert run.plan.semantic_execution_graph.semantic_graph_id == (
        application.child_graph.semantic_graph_id
    )
    assert run.plan.active_semantic_graph_revision_id == (
        application.revision.revision_id
    )
    assert len(run.plan.semantic_graph_revisions) == 1
    assert len(run.plan.semantic_graph_history) == 1
    snapshot = run.plan.semantic_graph_history[0]
    assert snapshot.graph.semantic_graph_id == parent.semantic_graph_id
    assert snapshot.edge_semantic_demands == old_demands
    assert snapshot.semantic_offers == old_offers
    assert snapshot.offer_demand_compatibilities == old_compatibilities
    assert snapshot.semantic_topology_neighborhoods == old_neighborhoods
    assert snapshot.semantic_join_evaluations == old_joins
    assert SemanticGraphRevisionAuthorityService().verify_snapshot(snapshot)

    assert run.plan.semantic_offers == []
    assert run.plan.offer_demand_compatibilities == []
    assert run.plan.semantic_topology_neighborhoods == []
    assert run.plan.semantic_join_evaluations == []
    assert run.plan.metadata["semantic_result_projection"]["status"] == (
        "invalidated_by_graph_revision"
    )
    assert run.plan.metadata["semantic_nway_projection"]["status"] == (
        "invalidated_by_graph_revision"
    )
    assert activation.demands_recompiled == len(
        application.child_graph.edges
    )
    assert len(run.plan.edge_semantic_demands) == len(
        application.child_graph.edges
    )
    assert all(
        demand.semantic_graph_id
        == application.child_graph.semantic_graph_id
        and demand.semantic_graph_authority_sha256
        == application.child_graph.authority_sha256
        for demand in run.plan.edge_semantic_demands
    )
    assert {
        demand.demand_id for demand in run.plan.edge_semantic_demands
    }.isdisjoint({demand.demand_id for demand in old_demands})


def test_new_consumer_without_original_canonical_step_activates_with_partial_demand() -> None:
    run = _run()
    graph = run.plan.semantic_execution_graph
    producer = next(
        unit for unit in graph.work_units if "step_a" in unit.source_step_ids
    )
    proposal = _proposal(
        run,
        add_work_units=[
            SemanticGraphRevisionWorkUnitAddition(
                addition_key="discovered_consumer",
                source_step_ids=["discovered_consumer_step"],
                semantic_goal="consume newly discovered evidence",
                work_modes=["analysis"],
                classification_status="explicit",
                required_capabilities=["analysis"],
            )
        ],
        add_edges=[
            SemanticGraphRevisionEdgeAddition(
                addition_key="producer_to_discovered_consumer",
                producer_ref=producer.work_unit_id,
                consumer_ref="addition:discovered_consumer",
                relation="semantic_dependency",
                required=True,
            )
        ],
    )
    application = SemanticGraphRevisionService().apply(
        run=run,
        proposal=proposal,
    )
    assert application.status == "applied"

    activation = SemanticGraphActivationService().activate(
        run=run,
        application=application,
    )

    assert activation.status == "activated"
    assert activation.partial_demands >= 1
    new_edge_id = application.revision.added_edge_ids[0]
    demand = next(
        item
        for item in run.plan.edge_semantic_demands
        if item.edge_id == new_edge_id
    )
    assert demand.status == "partial"
    assert demand.reason_codes == [
        "edge_semantic_requirements_unspecified"
    ]


def test_revision_chain_one_two_three_is_monotonic() -> None:
    run = _run()
    service = SemanticGraphRevisionService()
    activation_service = SemanticGraphActivationService()

    for number in (1, 2, 3):
        parent = run.plan.semantic_execution_graph
        parent_revision_id = (
            run.plan.semantic_graph_revisions[-1].revision_id
            if run.plan.semantic_graph_revisions
            else None
        )
        proposal = SemanticGraphRevisionProposal(
            parent_graph_id=parent.semantic_graph_id,
            parent_graph_authority_sha256=parent.authority_sha256,
            parent_revision_id=parent_revision_id,
            revision_number=number,
            reason=f"revision {number} adds discovered work",
            provenance={
                "source": "revision_chain_fixture",
                "revision_number": number,
            },
            add_work_units=[
                SemanticGraphRevisionWorkUnitAddition(
                    addition_key=f"discovered_unit_{number}",
                    source_step_ids=[f"discovered_step_{number}"],
                    semantic_goal=f"perform discovered work {number}",
                    work_modes=["analysis"],
                    classification_status="explicit",
                    required_capabilities=["analysis"],
                )
            ],
        )
        application = service.apply(run=run, proposal=proposal)
        assert application.status == "applied"
        activated = activation_service.activate(
            run=run,
            application=application,
        )
        assert activated.status == "activated"

    assert [item.revision_number for item in run.plan.semantic_graph_revisions] == [
        1,
        2,
        3,
    ]
    assert run.plan.semantic_graph_revisions[0].parent_revision_id is None
    assert run.plan.semantic_graph_revisions[1].parent_revision_id == (
        run.plan.semantic_graph_revisions[0].revision_id
    )
    assert run.plan.semantic_graph_revisions[2].parent_revision_id == (
        run.plan.semantic_graph_revisions[1].revision_id
    )
    assert len(run.plan.semantic_graph_history) == 3
    assert run.plan.active_semantic_graph_revision_id == (
        run.plan.semantic_graph_revisions[-1].revision_id
    )
    for index in range(1, 3):
        assert run.plan.semantic_graph_revisions[index].parent_graph_id == (
            run.plan.semantic_graph_revisions[index - 1].child_graph_id
        )


def test_non_monotonic_revision_is_rejected_before_application() -> None:
    run = _run()
    first = SemanticGraphRevisionService().apply(
        run=run,
        proposal=_proposal(run),
    )
    assert first.status == "applied"
    assert SemanticGraphActivationService().activate(
        run=run,
        application=first,
    ).status == "activated"

    parent = run.plan.semantic_execution_graph
    invalid = SemanticGraphRevisionProposal(
        parent_graph_id=parent.semantic_graph_id,
        parent_graph_authority_sha256=parent.authority_sha256,
        parent_revision_id=run.plan.semantic_graph_revisions[-1].revision_id,
        revision_number=4,
        reason="invalid revision jump",
        provenance={"source": "fixture"},
        add_work_units=[
            SemanticGraphRevisionWorkUnitAddition(
                addition_key="invalid_jump",
                source_step_ids=["invalid_jump_step"],
                semantic_goal="invalid jump",
                work_modes=["analysis"],
                classification_status="explicit",
                required_capabilities=["analysis"],
            )
        ],
    )

    result = SemanticGraphRevisionService().apply(
        run=run,
        proposal=invalid,
    )

    assert result.status == "blocked"
    assert result.reason_codes == ["GRAPH_REVISION_NUMBER_INVALID"]


def test_activation_failure_preserves_current_parent_state() -> None:
    run = _run()
    parent_before = deepcopy(run.plan.model_dump(mode="json"))
    application = SemanticGraphRevisionService().apply(
        run=run,
        proposal=_proposal(run),
    )
    assert application.status == "applied"
    assert application.child_graph is not None
    application.child_graph.authority_sha256 = "0" * 64

    activation = SemanticGraphActivationService().activate(
        run=run,
        application=application,
    )

    assert activation.status == "insufficient_contract_evidence"
    assert activation.reason_codes == [
        "GRAPH_ACTIVATION_CHILD_GRAPH_AUTHORITY_INVALID"
    ]
    assert run.plan.model_dump(mode="json") == parent_before
