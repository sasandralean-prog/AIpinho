from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from aipinho.schemas.runtime.execution_plan import (
    CanonicalExecutionPlan,
    CanonicalExecutionStep,
)
from aipinho.schemas.runtime.runtime_timeline import (
    RuntimeTimeline,
    RuntimeTimelineCompletion,
    RuntimeTimelineEvent,
    RuntimeTimelineValidation,
)
from aipinho.schemas.runtime.task_completion import TaskCompletionEvaluation
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
from aipinho.services.runtime.canonical_operation_state_service import (
    CanonicalOperationStateService,
)
from aipinho.services.runtime.runtime_truth_engine import RuntimeTruthEngine
from aipinho.services.semantics.edge_semantic_demand_compiler_service import (
    EdgeSemanticDemandCompilerService,
)
from aipinho.services.semantics.offer_demand_compatibility_service import (
    OfferDemandCompatibilityService,
)
from aipinho.services.semantics.semantic_completion_truth_service import (
    SemanticCompletionTruthService,
)
from aipinho.services.semantics.semantic_execution_graph_compiler_service import (
    SemanticExecutionGraphCompilerService,
)
from aipinho.services.semantics.semantic_nway_projection_service import (
    SemanticNWayProjectionService,
)
from aipinho.services.semantics.semantic_offer_compiler_service import (
    SemanticOfferCompilerService,
)
from aipinho.services.semantics.task_semantic_vocabulary_compiler_service import (
    TaskSemanticVocabularyCompilerService,
)


def _consumer_step(step_id: str, domain: str) -> CanonicalExecutionStep:
    return CanonicalExecutionStep(
        step_id=step_id,
        step_type="analyze",
        action=f"analyze_{domain}",
        required_capabilities=["analysis"],
        metadata={
            "work_modes": ["analysis"],
            "required_use_safety": {"safe_for_analysis": [True]},
            "required_evidence_domains": [f"{domain}_evidence"],
            "evidence_required": True,
        },
    )


def _build_run(domain: str, topology: str):
    producer_ids = ["producer_a"]
    consumer_ids = ["consumer_a"]
    if topology == "fan_in":
        producer_ids.append("producer_b")
    if topology == "fan_out":
        consumer_ids.append("consumer_b")

    steps = [
        CanonicalExecutionStep(
            step_id=step_id,
            step_type="observe",
            action=f"observe_{domain}",
            required_capabilities=["read_workspace"],
            metadata={"work_modes": ["observation"]},
        )
        for step_id in producer_ids
    ]
    steps.extend(_consumer_step(step_id, domain) for step_id in consumer_ids)
    canonical = CanonicalExecutionPlan(
        semantic_goal=f"evaluate {domain} evidence",
        operation_kind=f"{domain}_{topology}",
        execution_steps=steps,
        required_capabilities=["read_workspace", "analysis"],
        rollback_strategy={"required": False},
        trace_id=f"trace_{domain}_{topology}",
        metadata={"semantic_intent_graph": {"knowledge_output": True}},
    )
    plan = TaskRunPlan(
        plan_id=f"plan_{domain}_{topology}",
        contract_type=f"{domain}_contract",
        canonical_execution_plan=canonical,
    )
    run = SimpleNamespace(
        run_id=f"task_run_{domain}_{topology}",
        task_id=f"task_{domain}_{topology}",
        operation_id=f"operation_{domain}_{topology}",
        plan=plan,
        intent_map={"domain": domain},
        capabilities_required=list(canonical.required_capabilities),
        status="completed",
        workflow=SimpleNamespace(
            status="completed",
            workflow_id=f"workflow_{domain}_{topology}",
            current_phase=None,
        ),
        required_artifacts=[],
        produced_artifacts=[],
        contract_type=f"{domain}_contract",
        operation_type=f"{domain}_{topology}",
        runtime_profile="synthetic_generalization",
        block_cause=None,
        blocked_reasons=[],
    )
    vocabulary = TaskSemanticVocabularyCompilerService().compile_for_run(run=run)
    assert vocabulary.status == "compiled"
    assert vocabulary.vocabulary is not None
    plan.task_semantic_vocabulary = vocabulary.vocabulary

    work_units = [
        SemanticWorkUnitCandidate(
            unit_key=step_id,
            source_step_ids=[step_id],
            semantic_goal=f"observe {domain}",
            work_modes=["observation"],
            required_capabilities=["read_workspace"],
        )
        for step_id in producer_ids
    ]
    work_units.extend(
        SemanticWorkUnitCandidate(
            unit_key=step_id,
            source_step_ids=[step_id],
            semantic_goal=f"analyze {domain}",
            work_modes=["analysis"],
            required_capabilities=["analysis"],
        )
        for step_id in consumer_ids
    )
    if topology == "linear":
        edge_pairs = [("producer_a", "consumer_a")]
    elif topology == "fan_in":
        edge_pairs = [
            ("producer_a", "consumer_a"),
            ("producer_b", "consumer_a"),
        ]
    elif topology == "fan_out":
        edge_pairs = [
            ("producer_a", "consumer_a"),
            ("producer_a", "consumer_b"),
        ]
    else:
        raise AssertionError(f"unsupported topology: {topology}")

    graph_result = SemanticExecutionGraphCompilerService().compile_candidate_for_run(
        run=run,
        candidate=SemanticWorkDecompositionCandidate(
            work_units=work_units,
            edges=[
                SemanticDependencyEdgeCandidate(
                    producer_unit_key=producer,
                    consumer_unit_key=consumer,
                    relation="evidence_dependency",
                    required=True,
                )
                for producer, consumer in edge_pairs
            ],
            confidence=0.99,
            rationale=f"synthetic {topology} proof for {domain}",
        ),
    )
    assert graph_result.status == "accepted"
    assert graph_result.graph is not None
    plan.semantic_execution_graph = graph_result.graph

    demand_compiler = EdgeSemanticDemandCompilerService()
    plan.edge_semantic_demands = []
    for edge in graph_result.graph.edges:
        compiled = demand_compiler.compile_for_edge(
            run=run,
            edge_id=edge.edge_id,
        )
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
    step_id: str,
    *,
    limitations=None,
    evidence_domains=None,
):
    domain = run.intent_map["domain"]
    unit = _unit(run, step_id)
    observed = ObservedWorkUnitSemanticOutcome(
        producer_work_unit_id=unit.work_unit_id,
        source_step_ids=list(unit.source_step_ids),
        result_status="completed_with_limitations" if limitations else "completed",
        result_ref=f"task_run_result:{run.run_id}#{step_id}",
        observed_use_safety={"safe_for_analysis": True},
        evidence_domains=list(
            evidence_domains
            if evidence_domains is not None
            else [f"{domain}_evidence"]
        ),
        evidence_refs=[f"evidence:{domain}:{step_id}"],
        limitations=list(limitations or []),
        required_disclosures=(
            [f"{domain}_evidence_limited"] if limitations else []
        ),
        provenance={
            "source": "sprint9_synthetic_cross_domain",
            "domain": domain,
        },
    )
    result = SemanticOfferCompilerService().compile_for_work_unit(
        run=run,
        observed=observed,
    )
    assert result.status == "compiled"
    assert result.offer is not None
    return result.offer


def _materialize_semantics(run, offers) -> None:
    run.plan.semantic_offers = list(offers)
    run.plan.offer_demand_compatibilities = []
    offers_by_unit = {
        offer.producer_work_unit_id: offer for offer in offers
    }
    service = OfferDemandCompatibilityService()
    for demand in run.plan.edge_semantic_demands:
        result = service.evaluate(
            run=run,
            offer=offers_by_unit[demand.producer_work_unit_id],
            demand=demand,
        )
        assert result.status == "evaluated"
        assert result.compatibility is not None
        run.plan.offer_demand_compatibilities.append(result.compatibility)

    projection = SemanticNWayProjectionService().project(run=run)
    assert projection["status"] == "projected"


def _result(run) -> TaskRunResult:
    return TaskRunResult(
        run_id=run.run_id,
        status="completed",
        summary="synthetic workflow completed",
        completion=TaskCompletionEvaluation(
            status="completed",
            safe_to_report_success=True,
        ),
        validation={
            "validation_id": f"validation_{run.run_id}",
            "status": "passed",
        },
    )


def _timeline(run) -> RuntimeTimeline:
    return RuntimeTimeline(
        timeline_id=f"timeline_{run.run_id}",
        task_id=run.task_id,
        task_run_id=run.run_id,
        status="completed",
        events=[
            RuntimeTimelineEvent(
                event_id=f"event_terminal_{run.run_id}",
                sequence=1,
                timestamp="2026-09-15T00:00:00+00:00",
                task_id=run.task_id,
                task_run_id=run.run_id,
                event_type="run_completed",
                status="completed",
            )
        ],
        validations=[
            RuntimeTimelineValidation(
                validation_id=f"validation_{run.run_id}",
                status="passed",
            )
        ],
        completion=RuntimeTimelineCompletion(
            status="completed",
            safe_to_report_success=True,
            terminal_event_id=f"event_terminal_{run.run_id}",
        ),
    )


def _user_facing_truth(run):
    result = _result(run)
    timeline = _timeline(run)
    truth = RuntimeTruthEngine().evaluate(
        run,
        result=result,
        timeline=timeline,
    )
    canonical = CanonicalOperationStateService().derive(
        run,
        result=result,
        truth=truth,
        artifacts=[],
    )
    return truth, canonical


@pytest.mark.parametrize(
    ("domain", "topology"),
    [
        ("legal_brief_review", "linear"),
        ("industrial_sensor_fusion", "fan_in"),
        ("policy_notice_distribution", "fan_out"),
    ],
)
def test_unrelated_domains_and_topologies_reach_same_safe_truth_boundary(
    domain: str,
    topology: str,
) -> None:
    run = _build_run(domain, topology)
    producer_ids = {
        edge.producer_work_unit_id
        for edge in run.plan.semantic_execution_graph.edges
    }
    offers = [
        _compile_offer(run, unit.source_step_ids[0])
        for unit in run.plan.semantic_execution_graph.work_units
        if unit.work_unit_id in producer_ids
    ]
    _materialize_semantics(run, offers)

    facet = SemanticCompletionTruthService().evaluate(run)
    truth, canonical = _user_facing_truth(run)

    assert facet.status == "ready"
    assert facet.safe_to_report_success is True
    assert truth.status == "completed"
    assert truth.safe_to_report_success is True
    assert truth.speaker_truth_status == "allowed"
    assert canonical.status == "COMPLETED"
    assert canonical.safe_to_report_success is True


@pytest.mark.parametrize(
    ("domain", "topology"),
    [
        ("clinical_protocol_review", "linear"),
        ("satellite_measurement_fusion", "fan_in"),
    ],
)
def test_limitations_have_same_user_facing_effect_across_domains(
    domain: str,
    topology: str,
) -> None:
    run = _build_run(domain, topology)
    producer_steps = [
        unit.source_step_ids[0]
        for unit in run.plan.semantic_execution_graph.work_units
        if unit.work_modes == ["observation"]
    ]
    offers = [
        _compile_offer(
            run,
            step_id,
            limitations=["evidence_scope_limited"],
        )
        for step_id in producer_steps
    ]
    _materialize_semantics(run, offers)

    facet = SemanticCompletionTruthService().evaluate(run)
    truth, canonical = _user_facing_truth(run)

    assert facet.status == "constrained"
    assert facet.safe_to_report_success is False
    assert truth.status == "completed"
    assert truth.safe_to_report_success is False
    assert truth.speaker_truth_status == "evidence_required"
    assert canonical.status == "BLOCKED"
    assert canonical.safe_to_report_success is False


@pytest.mark.parametrize(
    ("domain", "topology"),
    [
        ("supply_chain_audit", "linear"),
        ("geospatial_observation_merge", "fan_in"),
    ],
)
def test_missing_domain_evidence_remains_unknown_and_fail_closed(
    domain: str,
    topology: str,
) -> None:
    run = _build_run(domain, topology)
    producer_steps = [
        unit.source_step_ids[0]
        for unit in run.plan.semantic_execution_graph.work_units
        if unit.work_modes == ["observation"]
    ]
    offers = [
        _compile_offer(
            run,
            step_id,
            evidence_domains=[] if index == 0 else None,
        )
        for index, step_id in enumerate(producer_steps)
    ]
    _materialize_semantics(run, offers)

    facet = SemanticCompletionTruthService().evaluate(run)
    truth, canonical = _user_facing_truth(run)

    assert facet.status == "insufficient_evidence"
    assert facet.safe_to_report_success is False
    assert truth.status == "blocked"
    assert truth.safe_to_report_success is False
    assert truth.reason_code == "semantic_truth_insufficient_evidence"
    assert canonical.status == "BLOCKED"


def test_semantic_truth_core_has_no_firetest_or_media_workflow_rules() -> None:
    root = Path(__file__).resolve().parents[2]
    core_files = [
        "src/aipinho/services/semantics/semantic_execution_graph_compiler_service.py",
        "src/aipinho/services/semantics/edge_semantic_demand_compiler_service.py",
        "src/aipinho/services/semantics/semantic_offer_compiler_service.py",
        "src/aipinho/services/semantics/offer_demand_compatibility_service.py",
        "src/aipinho/services/semantics/semantic_nway_topology_service.py",
        "src/aipinho/services/semantics/semantic_graph_revision_service.py",
        "src/aipinho/services/semantics/semantic_completion_truth_service.py",
        "src/aipinho/services/runtime/runtime_truth_engine.py",
        "src/aipinho/services/runtime_doctor/runtime_doctor_service.py",
    ]
    forbidden = (
        "firetest",
        "pinhoabacaxi",
        "novapinhomusic",
        "music_inventory",
        "phase_1",
        "phase_2",
    )
    matches = []
    for relative_path in core_files:
        text = (root / relative_path).read_text(encoding="utf-8").lower()
        for token in forbidden:
            if token in text:
                matches.append(f"{relative_path}:{token}")

    assert matches == []
