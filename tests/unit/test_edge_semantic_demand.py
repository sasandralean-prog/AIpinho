from __future__ import annotations

from types import SimpleNamespace

from aipinho.schemas.runtime.execution_plan import (
    CanonicalExecutionPlan,
    CanonicalExecutionStep,
)
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.semantics.semantic_execution_graph import (
    SemanticDependencyEdgeCandidate,
    SemanticWorkDecompositionCandidate,
    SemanticWorkUnitCandidate,
)
from aipinho.services.semantics.edge_semantic_demand_authority_service import (
    EdgeSemanticDemandAuthorityService,
)
from aipinho.services.semantics.edge_semantic_demand_compiler_service import (
    EdgeSemanticDemandCompilerService,
)
from aipinho.services.semantics.semantic_execution_graph_compiler_service import (
    SemanticExecutionGraphCompilerService,
)
from aipinho.services.semantics.task_semantic_vocabulary_compiler_service import (
    TaskSemanticVocabularyCompilerService,
)


def _run(*, invalid_property_state: bool = False):
    property_state = "readonly_analysis" if invalid_property_state else "observed"
    steps = [
        CanonicalExecutionStep(
            step_id="producer",
            step_type="observe",
            action="observe_source",
            required_capabilities=["read_workspace"],
            metadata={"work_modes": ["observation"]},
        ),
        CanonicalExecutionStep(
            step_id="consumer_catalog",
            step_type="analyze",
            action="build_catalog",
            required_capabilities=["analysis"],
            metadata={
                "work_modes": ["analysis"],
                "required_downstream_uses": ["catalog_planning"],
                "required_use_safety": {"safe_for_catalog": [True]},
                "required_semantic_properties": {
                    "content_identity": [property_state]
                },
                "required_evidence_domains": ["identity_evidence"],
                "evidence_required": True,
            },
        ),
        CanonicalExecutionStep(
            step_id="consumer_plan",
            step_type="plan",
            action="build_plan",
            required_capabilities=["planning"],
            metadata={
                "work_modes": ["planning"],
                "required_use_safety": {
                    "safe_for_planning": [True, "true_with_limitations"]
                },
                "required_evidence_domains": ["structure_evidence"],
                "prohibited_upstream_effects": ["destructive_action"],
                "evidence_required": True,
            },
        ),
    ]
    canonical = CanonicalExecutionPlan(
        semantic_goal="observe once and support two independent consumers",
        operation_kind="generic_fanout",
        execution_steps=steps,
        required_capabilities=["read_workspace", "analysis", "planning"],
        rollback_strategy={"required": False},
        trace_id="trace_edge_demand",
        metadata={"semantic_intent_graph": {"knowledge_output": True}},
    )
    plan = TaskRunPlan(
        plan_id="plan_edge_demand",
        contract_type="generic_fanout",
        canonical_execution_plan=canonical,
    )
    run = SimpleNamespace(
        run_id="task_run_edge_demand",
        task_id="task_edge_demand",
        plan=plan,
        intent_map={},
        capabilities_required=list(canonical.required_capabilities),
    )
    vocabulary = TaskSemanticVocabularyCompilerService().compile_for_run(run=run)
    assert vocabulary.status == "compiled"
    assert vocabulary.vocabulary is not None
    plan.task_semantic_vocabulary = vocabulary.vocabulary

    graph_candidate = SemanticWorkDecompositionCandidate(
        work_units=[
            SemanticWorkUnitCandidate(
                unit_key="producer",
                source_step_ids=["producer"],
                semantic_goal="observe source evidence",
                work_modes=["observation"],
                required_capabilities=["read_workspace"],
            ),
            SemanticWorkUnitCandidate(
                unit_key="catalog",
                source_step_ids=["consumer_catalog"],
                semantic_goal="analyze evidence for catalog use",
                work_modes=["analysis"],
                required_capabilities=["analysis"],
            ),
            SemanticWorkUnitCandidate(
                unit_key="plan",
                source_step_ids=["consumer_plan"],
                semantic_goal="plan from available evidence",
                work_modes=["planning"],
                required_capabilities=["planning"],
            ),
        ],
        edges=[
            SemanticDependencyEdgeCandidate(
                producer_unit_key="producer",
                consumer_unit_key="catalog",
                relation="evidence_dependency",
            ),
            SemanticDependencyEdgeCandidate(
                producer_unit_key="producer",
                consumer_unit_key="plan",
                relation="evidence_dependency",
            ),
        ],
        confidence=0.95,
        rationale="One observation feeds two independent consumers.",
    )
    graph_result = SemanticExecutionGraphCompilerService().compile_candidate_for_run(
        run=run,
        candidate=graph_candidate,
    )
    assert graph_result.status == "accepted"
    assert graph_result.graph is not None
    plan.semantic_execution_graph = graph_result.graph
    return run


def _edge_for_consumer(run, step_id: str):
    graph = run.plan.semantic_execution_graph
    consumer = next(
        unit for unit in graph.work_units if step_id in unit.source_step_ids
    )
    return next(
        edge
        for edge in graph.edges
        if edge.consumer_work_unit_id == consumer.work_unit_id
    )


def test_same_producer_can_have_distinct_edge_local_demands() -> None:
    run = _run()
    catalog_edge = _edge_for_consumer(run, "consumer_catalog")
    plan_edge = _edge_for_consumer(run, "consumer_plan")
    compiler = EdgeSemanticDemandCompilerService()

    catalog = compiler.compile_for_edge(run=run, edge_id=catalog_edge.edge_id)
    planning = compiler.compile_for_edge(run=run, edge_id=plan_edge.edge_id)

    assert catalog.status == "compiled"
    assert planning.status == "compiled"
    assert catalog.demand is not None
    assert planning.demand is not None
    assert catalog.demand.status == "ready"
    assert planning.demand.status == "ready"
    assert catalog.demand.producer_work_unit_id == planning.demand.producer_work_unit_id
    assert catalog.demand.consumer_work_unit_id != planning.demand.consumer_work_unit_id
    assert catalog.demand.required_downstream_uses == ["catalog_planning"]
    assert catalog.demand.required_use_safety == {"safe_for_catalog": [True]}
    assert catalog.demand.required_semantic_properties == {
        "content_identity": ["observed"]
    }
    assert catalog.demand.required_evidence_domains == ["identity_evidence"]
    assert planning.demand.required_downstream_uses == []
    assert planning.demand.required_use_safety == {
        "safe_for_planning": [True, "true_with_limitations"]
    }
    assert planning.demand.required_evidence_domains == ["structure_evidence"]
    assert planning.demand.prohibited_upstream_effects == ["destructive_action"]


def test_edge_demand_authority_detects_tampering() -> None:
    run = _run()
    edge = _edge_for_consumer(run, "consumer_catalog")
    result = EdgeSemanticDemandCompilerService().compile_for_edge(
        run=run,
        edge_id=edge.edge_id,
    )
    assert result.demand is not None
    authority = EdgeSemanticDemandAuthorityService()
    assert authority.verify(result.demand)

    result.demand.required_downstream_uses.append("tampered_use")
    assert not authority.verify(result.demand)


def test_semantic_dependency_without_explicit_requirements_is_partial() -> None:
    run = _run()
    graph = run.plan.semantic_execution_graph
    edge = _edge_for_consumer(run, "consumer_catalog")
    edge.relation = "semantic_dependency"
    consumer = next(
        unit
        for unit in graph.work_units
        if "consumer_catalog" in unit.source_step_ids
    )
    step = next(
        step
        for step in run.plan.canonical_execution_plan.execution_steps
        if step.step_id == "consumer_catalog"
    )
    step.metadata = {"work_modes": ["analysis"]}
    # Graph authority must be recomputed because relation changed only for fixture setup.
    from aipinho.services.semantics.semantic_execution_graph_authority_service import (
        SemanticExecutionGraphAuthorityService,
    )
    graph.authority_sha256 = SemanticExecutionGraphAuthorityService().compute_authority_sha256(
        task_run_id=graph.task_run_id,
        task_id=graph.task_id,
        source_plan_id=graph.source_plan_id,
        source_execution_id=graph.source_execution_id,
        source_semantics_sha256=graph.source_semantics_sha256,
        vocabulary_binding=graph.vocabulary_binding,
        work_units=graph.work_units,
        edges=graph.edges,
        status=graph.status,
        reason_codes=graph.reason_codes,
        schema_version=graph.schema_version,
    )

    result = EdgeSemanticDemandCompilerService().compile_for_edge(
        run=run,
        edge_id=edge.edge_id,
    )

    assert result.status == "compiled"
    assert result.demand is not None
    assert result.demand.status == "partial"
    assert result.demand.reason_codes == [
        "edge_semantic_requirements_unspecified"
    ]
    assert result.demand.consumer_work_unit_id == consumer.work_unit_id


def test_invalid_semantic_property_state_is_blocked() -> None:
    run = _run(invalid_property_state=True)
    edge = _edge_for_consumer(run, "consumer_catalog")

    result = EdgeSemanticDemandCompilerService().compile_for_edge(
        run=run,
        edge_id=edge.edge_id,
    )

    assert result.status == "blocked"
    assert result.reason_codes == [
        "EDGE_SEMANTIC_DEMAND_SEMANTIC_PROPERTY_INVALID"
    ]


def test_unknown_edge_fails_closed() -> None:
    run = _run()

    result = EdgeSemanticDemandCompilerService().compile_for_edge(
        run=run,
        edge_id="semantic_edge_missing",
    )

    assert result.status == "insufficient_contract_evidence"
    assert result.reason_codes == ["EDGE_SEMANTIC_DEMAND_EDGE_UNKNOWN"]


def test_graph_tampering_fails_closed() -> None:
    run = _run()
    edge = _edge_for_consumer(run, "consumer_catalog")
    run.plan.semantic_execution_graph.work_units[0].semantic_goal = "tampered"

    result = EdgeSemanticDemandCompilerService().compile_for_edge(
        run=run,
        edge_id=edge.edge_id,
    )

    assert result.status == "insufficient_contract_evidence"
    assert result.reason_codes == [
        "EDGE_SEMANTIC_DEMAND_GRAPH_AUTHORITY_INVALID"
    ]


def test_vocabulary_binding_mismatch_fails_closed() -> None:
    run = _run()
    edge = _edge_for_consumer(run, "consumer_catalog")
    original_graph = run.plan.semantic_execution_graph

    run.intent_map = {
        "required_downstream_uses": ["another_governed_use"],
    }
    recompiled = TaskSemanticVocabularyCompilerService().compile_for_run(run=run)
    assert recompiled.status == "compiled"
    assert recompiled.vocabulary is not None
    assert recompiled.vocabulary.authority_sha256 != (
        original_graph.vocabulary_binding.authority_sha256
    )
    run.plan.task_semantic_vocabulary = recompiled.vocabulary

    result = EdgeSemanticDemandCompilerService().compile_for_edge(
        run=run,
        edge_id=edge.edge_id,
    )

    assert result.status == "insufficient_contract_evidence"
    assert result.reason_codes == [
        "EDGE_SEMANTIC_DEMAND_VOCABULARY_BINDING_MISMATCH"
    ]
