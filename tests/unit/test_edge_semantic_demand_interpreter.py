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
from aipinho.services.semantics.edge_semantic_demand_interpreter_service import (
    EdgeSemanticDemandInterpreterService,
)
from aipinho.services.semantics.semantic_execution_graph_compiler_service import (
    SemanticExecutionGraphCompilerService,
)
from aipinho.services.semantics.task_semantic_vocabulary_compiler_service import (
    TaskSemanticVocabularyCompilerService,
)


class _Reasoner:
    def __init__(self, candidate: dict) -> None:
        self.candidate = candidate
        self.calls = 0

    def propose_json(self, **kwargs):
        self.calls += 1
        return {
            "status": "candidate",
            "candidate": self.candidate,
            "model_id": "fixture_model",
            "response_id": "fixture_response",
            "real_inference": False,
            "evaluation_status": "fixture",
            "warnings": [],
        }


def _candidate(*, evidence_required: bool = True) -> dict:
    return {
        "required_downstream_uses": [],
        "required_use_safety": {"safe_for_catalog": [True]},
        "required_semantic_properties": {},
        "required_evidence_domains": [],
        "required_upstream_effects": [],
        "prohibited_upstream_effects": [],
        "evidence_required": evidence_required,
        "base_constraints": [],
        "risk_constraints": [],
        "confidence": 0.9,
        "rationale": "Catalog safety is the minimum consumer requirement.",
    }


def _run(*, relation: str = "semantic_dependency", explicit: bool = False):
    consumer_metadata = {"work_modes": ["analysis"]}
    if explicit:
        consumer_metadata["required_use_safety"] = {
            "safe_for_catalog": [True]
        }
    steps = [
        CanonicalExecutionStep(
            step_id="producer",
            step_type="observe",
            action="observe",
            required_capabilities=["read_workspace"],
            metadata={"work_modes": ["observation"]},
        ),
        CanonicalExecutionStep(
            step_id="consumer",
            step_type="analyze",
            action="analyze",
            required_capabilities=["analysis"],
            metadata=consumer_metadata,
        ),
    ]
    canonical = CanonicalExecutionPlan(
        semantic_goal="observe then analyze",
        operation_kind="generic_analysis",
        execution_steps=steps,
        required_capabilities=["read_workspace", "analysis"],
        rollback_strategy={"required": False},
        trace_id="trace_edge_interpreter",
        metadata={"semantic_intent_graph": {"knowledge_output": True}},
    )
    plan = TaskRunPlan(
        plan_id="plan_edge_interpreter",
        contract_type="generic_analysis",
        canonical_execution_plan=canonical,
    )
    run = SimpleNamespace(
        run_id="task_run_edge_interpreter",
        task_id="task_edge_interpreter",
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
                    semantic_goal="observe",
                    work_modes=["observation"],
                    required_capabilities=["read_workspace"],
                ),
                SemanticWorkUnitCandidate(
                    unit_key="consumer",
                    source_step_ids=["consumer"],
                    semantic_goal="analyze",
                    work_modes=["analysis"],
                    required_capabilities=["analysis"],
                ),
            ],
            edges=[
                SemanticDependencyEdgeCandidate(
                    producer_unit_key="producer",
                    consumer_unit_key="consumer",
                    relation=relation,
                )
            ],
            confidence=0.95,
            rationale="Explicit fixture topology.",
        ),
    )
    assert graph.graph is not None
    plan.semantic_execution_graph = graph.graph
    return run, graph.graph.edges[0].edge_id


def test_interpreter_can_fill_partial_demand_without_authority() -> None:
    run, edge_id = _run()
    reasoner = _Reasoner(_candidate(evidence_required=True))
    result = EdgeSemanticDemandInterpreterService(
        reasoner=reasoner
    ).interpret_for_edge(run=run, edge_id=edge_id)

    assert reasoner.calls == 1
    assert result.status == "compiled"
    assert result.demand is not None
    assert result.demand.status == "ready"
    assert result.demand.required_use_safety == {
        "safe_for_catalog": [True]
    }
    assert result.semantic_interpretation["authority"] == (
        "deterministic_edge_semantic_demand_gate"
    )


def test_ready_explicit_demand_does_not_call_model() -> None:
    run, edge_id = _run(explicit=True)
    reasoner = _Reasoner(_candidate())
    result = EdgeSemanticDemandInterpreterService(
        reasoner=reasoner
    ).interpret_for_edge(run=run, edge_id=edge_id)

    assert reasoner.calls == 0
    assert result.status == "compiled"
    assert result.demand is not None
    assert result.demand.status == "ready"
    assert result.semantic_interpretation["status"] == "not_required"


def test_model_cannot_weaken_evidence_dependency() -> None:
    run, edge_id = _run(relation="evidence_dependency")
    reasoner = _Reasoner(_candidate(evidence_required=False))
    result = EdgeSemanticDemandInterpreterService(
        reasoner=reasoner
    ).interpret_for_edge(run=run, edge_id=edge_id)

    assert result.status == "blocked"
    assert result.reason_codes == [
        "EDGE_SEMANTIC_DEMAND_EVIDENCE_REQUIREMENT_WEAKENING"
    ]


def test_model_cannot_contradict_explicit_requirement() -> None:
    run, edge_id = _run(explicit=True)
    # Ready explicit demand means model is not consulted at all; the explicit
    # requirement remains canonical rather than being reopened for negotiation.
    reasoner = _Reasoner(
        {
            **_candidate(),
            "required_use_safety": {"safe_for_catalog": [False]},
        }
    )
    result = EdgeSemanticDemandInterpreterService(
        reasoner=reasoner
    ).interpret_for_edge(run=run, edge_id=edge_id)

    assert reasoner.calls == 0
    assert result.demand is not None
    assert result.demand.required_use_safety == {
        "safe_for_catalog": [True]
    }
