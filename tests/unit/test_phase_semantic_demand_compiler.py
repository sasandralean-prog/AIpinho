from types import SimpleNamespace

from aipinho.schemas.runtime.execution_plan import CanonicalExecutionPlan, CanonicalExecutionStep
from aipinho.schemas.runtime.phase_dependency_evaluation import (
    DownstreamPhaseRequirements,
    PhaseDependencySnapshot,
)
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.services.runtime.phase_dependency_contract_registry import PhaseDependencyContractRegistry
from aipinho.services.runtime.phase_dependency_evaluation_service import PhaseDependencyEvaluationService
from aipinho.services.runtime.phase_semantic_demand_compiler import PhaseSemanticDemandCompiler


class _SemanticInterpreter:
    def __init__(self, accepted_requirements: dict | None = None) -> None:
        self.accepted_requirements = dict(accepted_requirements or {})

    def interpret(self, *, source_payload: dict, semantic_graph: dict) -> dict:
        if not semantic_graph.get("knowledge_output"):
            return {
                "status": "not_required",
                "reason_code": None,
                "accepted_requirements": {},
                "provenance": {},
            }
        return {
            "status": "accepted",
            "reason_code": None,
            "accepted_requirements": {
                "required_downstream_uses": [],
                "required_use_safety": {},
                "required_semantic_properties": {},
                "base_constraints": [],
                "risk_constraints": [],
                **self.accepted_requirements,
            },
            "confidence": 0.91,
            "rationale": "fixture semantic demand",
            "provenance": {
                "model_id": "fixture-model",
                "response_id": "fixture-response",
                "real_inference": True,
                "evaluation_status": "accepted",
                "warnings": [],
                "authority": "deterministic_semantic_gate",
            },
        }


def _run(
    *,
    operation_type: str = "workspace_analysis_readonly",
    action: str = "project_analysis",
    side_effect: bool = False,
    semantic_graph: dict | None = None,
    required_capabilities: list[str] | None = None,
):
    step = CanonicalExecutionStep(
        step_id="step_consumer",
        step_type="consumer",
        action=action,
        side_effect=side_effect,
        required_capabilities=list(required_capabilities or ["read_workspace"]),
    )
    canonical = CanonicalExecutionPlan(
        semantic_goal="governed downstream operation",
        operation_kind=operation_type,
        execution_steps=[step],
        required_capabilities=list(required_capabilities or ["read_workspace"]),
        rollback_strategy={"required": side_effect},
        trace_id="trace_semantic_demand",
        metadata={"semantic_intent_graph": dict(semantic_graph or {})},
    )
    plan = TaskRunPlan(
        plan_id="plan_semantic_demand",
        contract_type="readonly_analysis",
        canonical_execution_plan=canonical,
    )
    return SimpleNamespace(plan=plan, operation_type=operation_type)


def _planning_graph() -> dict:
    return {
        "planning_intent": True,
        "readonly_contract": True,
        "prohibited_effects": ["workspace_mutation"],
    }


def test_same_phase_number_different_plan_operations_compile_different_demands() -> None:
    compiler = PhaseSemanticDemandCompiler()
    readonly = compiler.compile_for_run(
        run=_run(semantic_graph=_planning_graph()),
        consumer_phase_id="phase_2",
    )
    mutation = compiler.compile_for_run(
        run=_run(
            operation_type="workspace_change",
            action="write_files",
            side_effect=True,
            semantic_graph={"mutation_intent": True},
            required_capabilities=["write_workspace"],
        ),
        consumer_phase_id="phase_2",
    )

    assert readonly.status == mutation.status == "compiled"
    assert readonly.requirements is not None
    assert mutation.requirements is not None
    assert readonly.requirements.required_use_safety == {
        "safe_for_planning": [True, "true_with_limitations"]
    }
    assert mutation.requirements.required_use_safety == {
        "safe_for_destructive_action": [True]
    }


def test_phase_name_does_not_determine_semantic_requirements() -> None:
    compiler = PhaseSemanticDemandCompiler()
    run = _run(semantic_graph=_planning_graph())
    phase_two = compiler.compile_for_run(run=run, consumer_phase_id="phase_2")
    phase_later = compiler.compile_for_run(run=run, consumer_phase_id="phase_later")

    assert phase_two.requirements is not None
    assert phase_later.requirements is not None
    assert phase_two.requirements.required_use_safety == phase_later.requirements.required_use_safety
    assert phase_two.requirements.prohibited_effects == phase_later.requirements.prohibited_effects
    assert phase_two.source_semantics_sha256 == phase_later.source_semantics_sha256


def test_same_operation_with_different_canonical_intent_compiles_different_demand() -> None:
    compiler = PhaseSemanticDemandCompiler(
        semantic_interpreter=_SemanticInterpreter(
            {
                "required_use_safety": {
                    "safe_for_truth_claim": [True],
                }
            }
        )
    )
    planning = compiler.compile_for_run(
        run=_run(semantic_graph=_planning_graph()),
        consumer_phase_id="consumer",
    )
    truth_claim = compiler.compile_for_run(
        run=_run(semantic_graph={"knowledge_output": True, "readonly_contract": True}),
        consumer_phase_id="consumer",
    )

    assert planning.requirements is not None
    assert truth_claim.requirements is not None
    assert "safe_for_planning" in planning.requirements.required_use_safety
    assert truth_claim.requirements.required_use_safety["safe_for_truth_claim"] == [True]
    assert truth_claim.semantic_interpretation["status"] == "accepted"


def test_knowledge_output_can_compile_without_full_upstream_truth_requirement() -> None:
    compiler = PhaseSemanticDemandCompiler(
        semantic_interpreter=_SemanticInterpreter(
            {
                "required_use_safety": {
                    "safe_for_downstream_static_analysis": [
                        True,
                        "true_with_limitations",
                    ],
                },
                "base_constraints": ["do_not_promote_upstream_identity_to_truth"],
            }
        )
    )

    compilation = compiler.compile_for_run(
        run=_run(
            semantic_graph={
                "knowledge_output": True,
                "observational_intent": True,
                "readonly_contract": True,
            }
        ),
        consumer_phase_id="consumer",
    )

    assert compilation.status == "compiled"
    assert compilation.requirements is not None
    assert compilation.requirements.allowed_dependency_statuses == [
        "satisfied",
        "satisfied_with_limitations",
    ]
    assert "safe_for_truth_claim" not in compilation.requirements.required_use_safety
    assert compilation.requirements.required_use_safety[
        "safe_for_downstream_static_analysis"
    ] == [True, "true_with_limitations"]
    assert (
        "do_not_promote_upstream_identity_to_truth"
        in compilation.requirements.base_constraints
    )
    provenance = {
        item.requirement: item.source_kind
        for item in compilation.requirements.requirement_provenance
    }
    assert (
        provenance["required_use_safety:safe_for_downstream_static_analysis"]
        == "deterministic_semantic_gate"
    )


def test_compiled_requirements_are_frozen_before_upstream_evidence_is_observed() -> None:
    compilation = PhaseSemanticDemandCompiler().compile_for_run(
        run=_run(semantic_graph=_planning_graph()),
        consumer_phase_id="consumer",
    )
    assert compilation.requirements is not None
    before = compilation.requirements.model_dump(mode="json")
    upstream = PhaseDependencySnapshot(
        dependency_id="dependency",
        producer_task_run_id="producer",
        producer_operation_id="producer_operation",
        producer_phase_id="upstream",
        upstream_result_ref="result",
        dependency_status="satisfied_with_limitations",
    )
    upstream.limitations.append("newly_observed_limitation")

    assert compilation.requirements.model_dump(mode="json") == before
    assert compilation.requirements.frozen_at is not None


def test_requirements_hash_rejects_post_evaluation_contract_change() -> None:
    compiler = PhaseSemanticDemandCompiler()
    compilation = compiler.compile_for_run(
        run=_run(semantic_graph=_planning_graph()),
        consumer_phase_id="consumer",
    )
    requirements = compilation.requirements
    assert requirements is not None
    snapshot = PhaseDependencySnapshot(
        dependency_id="dependency",
        producer_task_run_id="producer",
        producer_operation_id="producer_operation",
        producer_phase_id="upstream",
        upstream_result_ref="result",
        dependency_status="satisfied",
        evidence_refs=["artifact:evidence"],
        use_safety={"safe_for_planning": True},
    )
    evaluator = PhaseDependencyEvaluationService()
    evaluation = evaluator.evaluate(
        snapshot=snapshot,
        requirements=requirements,
        consumer_task_run_id="consumer_run",
        consumer_operation_id="consumer_operation",
        consumer_operation_type=requirements.operation_type,
    )
    requirements.required_use_safety["safe_for_truth_claim"] = [True]

    admission = evaluator.authorize(
        evaluation=evaluation,
        requirements=requirements,
        consumer_task_run_id="consumer_run",
        consumer_operation_id="consumer_operation",
        consumer_operation_type=requirements.operation_type,
        producer_task_run_id=snapshot.producer_task_run_id,
        producer_operation_id=snapshot.producer_operation_id,
        dependency_id=snapshot.dependency_id,
        producer_phase_id=snapshot.producer_phase_id,
        consumer_phase_id=requirements.consumer_phase_id,
    )

    assert admission.authorized is False
    assert admission.reason_code == "PHASE_DEPENDENCY_EVALUATION_BINDING_MISMATCH"


def test_missing_canonical_downstream_plan_fails_closed() -> None:
    run = SimpleNamespace(plan=TaskRunPlan(plan_id="missing", contract_type="readonly_analysis"))

    compilation = PhaseSemanticDemandCompiler().compile_for_run(
        run=run,
        consumer_phase_id="consumer",
        consumer_operation_type="readonly_analysis",
    )

    assert compilation.status == "insufficient_contract_evidence"
    assert compilation.requirements is None
    assert compilation.reason_codes == ["PHASE_DEPENDENCY_DOWNSTREAM_CANONICAL_PLAN_REQUIRED"]


def test_missing_run_level_semantic_intent_fails_closed() -> None:
    compilation = PhaseSemanticDemandCompiler().compile_for_run(
        run=_run(semantic_graph={}),
        consumer_phase_id="consumer",
    )

    assert compilation.status == "insufficient_contract_evidence"
    assert compilation.requirements is None
    assert compilation.reason_codes == ["PHASE_DEPENDENCY_DOWNSTREAM_SEMANTIC_INTENT_REQUIRED"]


def test_system_invariants_only_strengthen_compiled_task_semantics() -> None:
    invariant = DownstreamPhaseRequirements(
        contract_id="system_invariant_readonly_planning",
        consumer_phase_id="*",
        operation_type="workspace_analysis_readonly",
        authority_source="system_invariant",
        allowed_dependency_statuses=["satisfied"],
        required_use_safety={"safe_for_truth_claim": [True]},
        required_capabilities=["policy_guard"],
        prohibited_effects=["network_write"],
        evidence_required=True,
    )
    compiler = PhaseSemanticDemandCompiler(
        system_invariants=PhaseDependencyContractRegistry([invariant])
    )

    compilation = compiler.compile_for_run(
        run=_run(semantic_graph=_planning_graph()),
        consumer_phase_id="consumer",
    )

    assert compilation.status == "compiled"
    assert compilation.requirements is not None
    assert compilation.requirements.allowed_dependency_statuses == ["satisfied"]
    assert compilation.requirements.required_use_safety == {
        "safe_for_planning": [True, "true_with_limitations"],
        "safe_for_truth_claim": [True],
    }
    assert "policy_guard" in compilation.requirements.required_capabilities
    assert "network_write" in compilation.requirements.prohibited_effects
    assert compilation.requirements.authority_source == "compiled_task_semantics_with_system_invariants"


def test_evaluator_rejects_compiled_requirements_without_source_provenance() -> None:
    compilation = PhaseSemanticDemandCompiler().compile_for_run(
        run=_run(semantic_graph=_planning_graph()),
        consumer_phase_id="consumer",
    )
    requirements = compilation.requirements
    assert requirements is not None
    requirements.requirement_provenance = []
    evaluation = PhaseDependencyEvaluationService().evaluate(
        snapshot=PhaseDependencySnapshot(
            dependency_id="dependency",
            producer_task_run_id="producer",
            producer_operation_id="producer_operation",
            producer_phase_id="upstream",
            upstream_result_ref="result",
            dependency_status="satisfied",
            evidence_refs=["artifact:evidence"],
            use_safety={"safe_for_planning": True},
        ),
        requirements=requirements,
        consumer_task_run_id="consumer_run",
        consumer_operation_id="consumer_operation",
        consumer_operation_type=requirements.operation_type,
    )

    assert evaluation.decision == "INSUFFICIENT_EVIDENCE"
    assert evaluation.evaluation_status == "incomplete"
    assert "PHASE_DEPENDENCY_COMPILED_REQUIREMENTS_PROVENANCE_REQUIRED" in evaluation.reason_codes


def test_every_compiled_requirement_has_explicit_source_provenance() -> None:
    compilation = PhaseSemanticDemandCompiler().compile_for_run(
        run=_run(semantic_graph=_planning_graph()),
        consumer_phase_id="consumer",
    )

    assert compilation.status == "compiled"
    assert compilation.requirements is not None
    provenance = {item.requirement for item in compilation.requirements.requirement_provenance}
    assert "operation_type" in provenance
    assert "allowed_dependency_statuses" in provenance
    assert "evidence_required" in provenance
    assert "required_use_safety:safe_for_planning" in provenance
    assert "required_capability:read_workspace" in provenance
    assert "prohibited_effect:workspace_mutation" in provenance
