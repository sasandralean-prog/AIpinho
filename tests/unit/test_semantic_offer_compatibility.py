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
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.schemas.semantics.semantic_offer import (
    ObservedWorkUnitSemanticOutcome,
)
from aipinho.services.semantics.edge_semantic_demand_compiler_service import (
    EdgeSemanticDemandCompilerService,
)
from aipinho.services.semantics.offer_demand_compatibility_authority_service import (
    OfferDemandCompatibilityAuthorityService,
)
from aipinho.services.semantics.offer_demand_compatibility_service import (
    OfferDemandCompatibilityService,
)
from aipinho.services.semantics.semantic_execution_graph_compiler_service import (
    SemanticExecutionGraphCompilerService,
)
from aipinho.services.semantics.semantic_offer_authority_service import (
    SemanticOfferAuthorityService,
)
from aipinho.services.semantics.semantic_offer_compiler_service import (
    SemanticOfferCompilerService,
)
from aipinho.services.semantics.observed_work_unit_outcome_projection_service import (
    ObservedWorkUnitOutcomeProjectionService,
)
from aipinho.services.semantics.semantic_result_projection_service import (
    SemanticResultProjectionService,
)
from aipinho.services.semantics.task_semantic_vocabulary_compiler_service import (
    TaskSemanticVocabularyCompilerService,
)


def _run():
    steps = [
        CanonicalExecutionStep(
            step_id="producer",
            step_type="observe",
            action="observe",
            required_capabilities=["read_workspace"],
            metadata={"work_modes": ["observation"]},
        ),
        CanonicalExecutionStep(
            step_id="catalog_consumer",
            step_type="analyze",
            action="catalog",
            required_capabilities=["analysis"],
            metadata={
                "work_modes": ["analysis"],
                "required_downstream_uses": ["catalog_planning"],
                "required_use_safety": {"safe_for_catalog": [True]},
                "required_semantic_properties": {
                    "content_identity": ["observed"]
                },
                "required_evidence_domains": ["identity_evidence"],
                "evidence_required": True,
            },
        ),
        CanonicalExecutionStep(
            step_id="planning_consumer",
            step_type="plan",
            action="plan",
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
        semantic_goal="one producer supports two consumers",
        operation_kind="fanout",
        execution_steps=steps,
        required_capabilities=["read_workspace", "analysis", "planning"],
        rollback_strategy={"required": False},
        trace_id="trace_offer_compatibility",
        metadata={"semantic_intent_graph": {"knowledge_output": True}},
    )
    plan = TaskRunPlan(
        plan_id="plan_offer_compatibility",
        contract_type="generic_fanout",
        canonical_execution_plan=canonical,
    )
    run = SimpleNamespace(
        run_id="task_run_offer_compatibility",
        task_id="task_offer_compatibility",
        plan=plan,
        intent_map={},
        capabilities_required=list(canonical.required_capabilities),
    )
    vocabulary = TaskSemanticVocabularyCompilerService().compile_for_run(run=run)
    assert vocabulary.status == "compiled"
    assert vocabulary.vocabulary is not None
    plan.task_semantic_vocabulary = vocabulary.vocabulary

    graph = SemanticExecutionGraphCompilerService().compile_candidate_for_run(
        run=run,
        candidate=SemanticWorkDecompositionCandidate(
            work_units=[
                SemanticWorkUnitCandidate(
                    unit_key="producer",
                    source_step_ids=["producer"],
                    semantic_goal="observe source",
                    work_modes=["observation"],
                    required_capabilities=["read_workspace"],
                ),
                SemanticWorkUnitCandidate(
                    unit_key="catalog",
                    source_step_ids=["catalog_consumer"],
                    semantic_goal="consume for catalog",
                    work_modes=["analysis"],
                    required_capabilities=["analysis"],
                ),
                SemanticWorkUnitCandidate(
                    unit_key="planning",
                    source_step_ids=["planning_consumer"],
                    semantic_goal="consume for planning",
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
                    consumer_unit_key="planning",
                    relation="evidence_dependency",
                ),
            ],
            confidence=0.95,
            rationale="One observation feeds two different consumers.",
        ),
    )
    assert graph.status == "accepted"
    assert graph.graph is not None
    plan.semantic_execution_graph = graph.graph

    demands = []
    compiler = EdgeSemanticDemandCompilerService()
    for edge in graph.graph.edges:
        result = compiler.compile_for_edge(run=run, edge_id=edge.edge_id)
        assert result.status == "compiled"
        assert result.demand is not None
        demands.append(result.demand)
    plan.edge_semantic_demands = demands
    return run


def _producer(run):
    return next(
        unit
        for unit in run.plan.semantic_execution_graph.work_units
        if "producer" in unit.source_step_ids
    )


def _demand(run, consumer_step_id: str):
    consumer = next(
        unit
        for unit in run.plan.semantic_execution_graph.work_units
        if consumer_step_id in unit.source_step_ids
    )
    return next(
        demand
        for demand in run.plan.edge_semantic_demands
        if demand.consumer_work_unit_id == consumer.work_unit_id
    )


def _offer(
    run,
    *,
    planning_safe=False,
    semantic_property="observed",
    limitations=None,
    evidence_domains=None,
):
    producer = _producer(run)
    observed = ObservedWorkUnitSemanticOutcome(
        producer_work_unit_id=producer.work_unit_id,
        source_step_ids=list(producer.source_step_ids),
        result_status="completed_with_limitations" if limitations else "completed",
        result_ref="task_run_result:fixture",
        observed_use_safety={
            "safe_for_catalog": True,
            "safe_for_planning": planning_safe,
        },
        observed_semantic_properties={
            "content_identity": semantic_property,
        },
        allowed_downstream_uses=["catalog_planning"],
        evidence_domains=list(
            evidence_domains
            if evidence_domains is not None
            else ["identity_evidence", "structure_evidence"]
        ),
        observed_effects=[],
        evidence_refs=["evidence:producer"],
        artifact_refs=["artifact:producer"],
        limitations=list(limitations or []),
        required_disclosures=(
            ["producer_has_limitations"] if limitations else []
        ),
        provenance={
            "source": "synthetic_work_unit_result",
            "result_ref": "task_run_result:fixture",
        },
    )
    result = SemanticOfferCompilerService().compile_for_work_unit(
        run=run,
        observed=observed,
    )
    assert result.status == "compiled"
    assert result.offer is not None
    return result.offer


def test_same_offer_can_be_admitted_for_one_consumer_and_blocked_for_another() -> None:
    run = _run()
    offer = _offer(run, planning_safe=False)
    catalog = _demand(run, "catalog_consumer")
    planning = _demand(run, "planning_consumer")
    service = OfferDemandCompatibilityService()

    catalog_result = service.evaluate(
        run=run,
        offer=offer,
        demand=catalog,
    )
    planning_result = service.evaluate(
        run=run,
        offer=offer,
        demand=planning,
    )

    assert catalog_result.compatibility is not None
    assert planning_result.compatibility is not None
    assert catalog_result.compatibility.decision == "admitted"
    assert planning_result.compatibility.decision == "blocked"
    assert catalog_result.compatibility.offer_id == planning_result.compatibility.offer_id
    assert offer.use_safety["safe_for_planning"] is False


def test_unknown_semantic_property_is_insufficient_not_false() -> None:
    run = _run()
    offer = _offer(run, semantic_property="unknown")
    demand = _demand(run, "catalog_consumer")

    result = OfferDemandCompatibilityService().evaluate(
        run=run,
        offer=offer,
        demand=demand,
    )

    assert result.compatibility is not None
    assert result.compatibility.decision == "insufficient_evidence"
    assert "semantic_property:content_identity" in (
        result.compatibility.unknown_dimensions
    )
    assert result.compatibility.blocked_dimensions == []


def test_partial_offer_with_satisfied_requirements_is_admitted_with_constraints() -> None:
    run = _run()
    offer = _offer(
        run,
        planning_safe=True,
        limitations=["identity_scope_limited"],
    )
    demand = _demand(run, "catalog_consumer")

    result = OfferDemandCompatibilityService().evaluate(
        run=run,
        offer=offer,
        demand=demand,
    )

    assert result.compatibility is not None
    assert result.compatibility.decision == "admitted_with_constraints"
    assert "limitation:identity_scope_limited" in (
        result.compatibility.disclosures
    )


def test_missing_required_evidence_domain_is_insufficient() -> None:
    run = _run()
    offer = _offer(
        run,
        planning_safe=True,
        evidence_domains=["identity_evidence"],
    )
    demand = _demand(run, "planning_consumer")

    result = OfferDemandCompatibilityService().evaluate(
        run=run,
        offer=offer,
        demand=demand,
    )

    assert result.compatibility is not None
    assert result.compatibility.decision == "insufficient_evidence"
    assert "evidence_domain:structure_evidence" in (
        result.compatibility.unknown_dimensions
    )


def test_offer_and_compatibility_authorities_detect_tampering() -> None:
    run = _run()
    offer = _offer(run, planning_safe=True)
    demand = _demand(run, "catalog_consumer")
    result = OfferDemandCompatibilityService().evaluate(
        run=run,
        offer=offer,
        demand=demand,
    )
    assert result.compatibility is not None

    offer_authority = SemanticOfferAuthorityService()
    compatibility_authority = OfferDemandCompatibilityAuthorityService()
    assert offer_authority.verify(offer)
    assert compatibility_authority.verify(result.compatibility)

    offer.use_safety["safe_for_catalog"] = False
    assert not offer_authority.verify(offer)
    assert compatibility_authority.verify(result.compatibility)


def test_offer_source_step_binding_mismatch_is_blocked() -> None:
    run = _run()
    producer = _producer(run)
    observed = ObservedWorkUnitSemanticOutcome(
        producer_work_unit_id=producer.work_unit_id,
        source_step_ids=["catalog_consumer"],
        result_status="completed",
        result_ref="task_run_result:fixture",
        provenance={"source": "fixture"},
    )

    result = SemanticOfferCompilerService().compile_for_work_unit(
        run=run,
        observed=observed,
    )

    assert result.status == "blocked"
    assert result.reason_codes == [
        "SEMANTIC_OFFER_SOURCE_STEP_BINDING_MISMATCH"
    ]


def _terminal_result(*, producer_output: dict | None = None) -> TaskRunResult:
    return TaskRunResult(
        run_id="task_run_offer_compatibility",
        status="completed",
        summary="completed",
        step_summaries=[
            {
                "step_id": "producer",
                "step_type": "observe",
                "status": "completed",
                "output_summary": dict(producer_output or {}),
                "warnings": [],
                "violations": [],
            },
            {
                "step_id": "catalog_consumer",
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


def test_work_unit_projection_reads_only_explicit_semantic_outcome_envelope() -> None:
    run = _run()
    result = _terminal_result(
        producer_output={
            "semantic_outcome": {
                "use_safety": {
                    "safe_for_catalog": True,
                    "safe_for_planning": False,
                },
                "semantic_properties": {
                    "content_identity": "observed",
                },
                "allowed_downstream_uses": ["catalog_planning"],
                "evidence_domains": [
                    "identity_evidence",
                    "structure_evidence",
                ],
                "evidence_refs": ["evidence:producer"],
                "artifact_refs": ["artifact:producer"],
            }
        }
    )

    projected = ObservedWorkUnitOutcomeProjectionService().project(
        run=run,
        result=result,
    )
    producer = next(
        item
        for item in projected
        if item.source_step_ids == ["producer"]
    )

    assert producer.observed_use_safety == {
        "safe_for_catalog": True,
        "safe_for_planning": False,
    }
    assert producer.observed_semantic_properties == {
        "content_identity": "observed"
    }
    assert producer.allowed_downstream_uses == ["catalog_planning"]
    assert producer.evidence_refs == ["evidence:producer"]


def test_free_form_output_does_not_become_semantic_offer_truth() -> None:
    run = _run()
    result = _terminal_result(
        producer_output={
            "safe_for_catalog": True,
            "content_identity": "observed",
            "evidence_domains": ["identity_evidence"],
        }
    )

    projection = SemanticResultProjectionService().project(
        run=run,
        result=result,
    )
    producer = _producer(run)
    offer = next(
        item
        for item in run.plan.semantic_offers
        if item.producer_work_unit_id == producer.work_unit_id
    )

    assert projection["status"] == "projected"
    assert offer.status == "unknown"
    assert offer.use_safety == {}
    assert offer.semantic_properties == {}
    assert offer.evidence_domains == []


def test_runtime_projection_persists_fanout_compatibility_from_one_offer() -> None:
    run = _run()
    result = _terminal_result(
        producer_output={
            "semantic_outcome": {
                "use_safety": {
                    "safe_for_catalog": True,
                    "safe_for_planning": False,
                },
                "semantic_properties": {
                    "content_identity": "observed",
                },
                "allowed_downstream_uses": ["catalog_planning"],
                "evidence_domains": [
                    "identity_evidence",
                    "structure_evidence",
                ],
                "evidence_refs": ["evidence:producer"],
            }
        }
    )

    projection = SemanticResultProjectionService().project(
        run=run,
        result=result,
    )

    assert projection["offers_compiled"] == 3
    assert projection["compatibilities_evaluated"] == 2
    decisions = {
        item.consumer_work_unit_id: item.decision
        for item in run.plan.offer_demand_compatibilities
    }
    catalog_demand = _demand(run, "catalog_consumer")
    planning_demand = _demand(run, "planning_consumer")
    assert decisions[catalog_demand.consumer_work_unit_id] == "admitted"
    assert decisions[planning_demand.consumer_work_unit_id] == "blocked"


def test_absent_positive_offer_fact_remains_unknown() -> None:
    run = _run()
    offer = _offer(
        run,
        planning_safe=True,
        evidence_domains=["identity_evidence", "structure_evidence"],
    )
    offer.allowed_downstream_uses = []
    authority = SemanticOfferAuthorityService()
    offer.authority_sha256 = authority.compute_authority_sha256(offer)
    demand = _demand(run, "catalog_consumer")

    result = OfferDemandCompatibilityService().evaluate(
        run=run,
        offer=offer,
        demand=demand,
    )

    assert result.compatibility is not None
    assert result.compatibility.decision == "insufficient_evidence"
    assert "downstream_use:catalog_planning" in (
        result.compatibility.unknown_dimensions
    )
    assert "downstream_use:catalog_planning" not in (
        result.compatibility.blocked_dimensions
    )
