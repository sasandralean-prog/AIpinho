from __future__ import annotations

from types import SimpleNamespace

from aipinho.schemas.runtime.execution_plan import (
    CanonicalExecutionPlan,
    CanonicalExecutionStep,
)
from aipinho.schemas.runtime.phase_dependency_evaluation import (
    DownstreamPhaseRequirements,
    PhaseDependencySnapshot,
)
from aipinho.services.semantics.limitation_compatibility_resolver_service import (
    LimitationCompatibilityResolverService,
)
from aipinho.services.semantics.semantic_demand_interpreter_service import (
    SemanticDemandInterpreterService,
)
from aipinho.services.semantics.semantic_reasoning_playbook_service import (
    SemanticReasoningPlaybookService,
)
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.services.semantics.task_semantic_vocabulary_compiler_service import (
    TaskSemanticVocabularyCompilerService,
)


class _Reasoner:
    def __init__(self, response: dict) -> None:
        self.response = response

    def propose_json(self, **kwargs):
        return dict(self.response)


class _PayloadReasoner:
    def __init__(self, builder) -> None:
        self.builder = builder
        self.last_kwargs = None

    def propose_json(self, **kwargs):
        self.last_kwargs = kwargs
        return _candidate(self.builder(kwargs))


def _candidate(candidate: dict, *, model_id: str = "fixture-model") -> dict:
    structured = {
        "resolution_status": "resolved",
        "unresolved_reason_codes": [],
        **candidate,
    }
    return {
        "status": "candidate",
        "candidate": structured,
        "model_id": model_id,
        "response_id": "fixture-response",
        "real_inference": True,
        "evaluation_status": "accepted",
        "warnings": [],
    }


def _source_payload() -> dict:
    return {
        "semantic_goal": "readonly static analysis",
        "operation_kind": "workspace_analysis_readonly",
        "intent_map": {"operation_type": "readonly_analysis"},
        "targets": ["workspace"],
        "artifact_expectations": ["analysis.md"],
        "requested_deliverables": ["analysis report"],
        "required_capabilities": ["read_workspace"],
        "semantic_intent_graph": {
            "knowledge_output": True,
            "observational_intent": True,
            "readonly_contract": True,
        },
        "steps": [{"action": "project_analysis", "side_effect": False}],
    }


def _vocabulary():
    payload = _source_payload()
    step = CanonicalExecutionStep(
        step_id="step1",
        step_type="analysis",
        action="project_analysis",
        side_effect=False,
        required_capabilities=["read_workspace"],
    )
    canonical = CanonicalExecutionPlan(
        semantic_goal=payload["semantic_goal"],
        operation_kind=payload["operation_kind"],
        execution_steps=[step],
        required_capabilities=["read_workspace"],
        rollback_strategy={},
        trace_id="trace_hybrid_semantics",
        metadata={
            "semantic_intent_graph": payload["semantic_intent_graph"],
            "requested_deliverables": payload["requested_deliverables"],
        },
    )
    plan = TaskRunPlan(
        plan_id="plan_hybrid_semantics",
        contract_type="readonly_analysis",
        canonical_execution_plan=canonical,
    )
    run = SimpleNamespace(
        plan=plan,
        run_id="task_run_hybrid_semantics",
        task_id="task_hybrid_semantics",
        intent_map=payload["intent_map"],
        capabilities_required=["read_workspace"],
    )
    compilation = TaskSemanticVocabularyCompilerService().compile_for_run(run=run)
    assert compilation.status == "compiled"
    assert compilation.vocabulary is not None
    return compilation.vocabulary


def test_semantic_reasoning_playbook_exposes_governed_vocabulary_without_copying_examples() -> None:
    payload = _source_payload()
    context = SemanticReasoningPlaybookService().build(
        source_payload=payload,
        vocabulary=_vocabulary(),
    )
    vocabulary = context["governed_vocabulary"]

    assert "safe_for_truth_claim" in vocabulary["use_safety_dimensions"]
    assert "safe_for_downstream_static_analysis" in vocabulary["use_safety_dimensions"]
    assert vocabulary["use_safety_allowed_states"][
        "safe_for_downstream_static_analysis"
    ] == [True, "true_with_limitations", False]
    assert vocabulary["use_safety_requirement_states"][
        "safe_for_downstream_static_analysis"
    ] == [True, "true_with_limitations"]
    assert "analysis report" not in vocabulary["downstream_use_identifiers"]
    assert "safe_for_operation_Y" not in vocabulary["use_safety_dimensions"]
    assert context["generic_examples"]
    assert context["generic_counterexamples"]
    assert "Do not copy identifiers or values" in context["authority_notice"]


def test_semantic_demand_interpreter_accepts_scoped_non_truth_demand() -> None:
    service = SemanticDemandInterpreterService(
        reasoner=_Reasoner(
            _candidate(
                {
                    "truth_claim_required": False,
                    "required_downstream_uses": [],
                    "required_use_safety": {
                        "safe_for_downstream_static_analysis": [
                            True,
                            "true_with_limitations",
                        ]
                    },
                    "required_semantic_properties": {},
                    "base_constraints": [
                        "do_not_promote_upstream_identity_to_truth"
                    ],
                    "risk_constraints": [],
                    "confidence": 0.91,
                    "rationale": "The downstream task analyzes implementation behavior.",
                }
            )
        )
    )

    result = service.interpret(
        source_payload=_source_payload(),
        semantic_graph=_source_payload()["semantic_intent_graph"],
        vocabulary=_vocabulary(),
    )

    assert result["status"] == "accepted"
    accepted = result["accepted_requirements"]
    assert "safe_for_truth_claim" not in accepted["required_use_safety"]
    assert accepted["required_use_safety"][
        "safe_for_downstream_static_analysis"
    ] == [True, "true_with_limitations"]
    assert result["provenance"]["authority"] == "deterministic_semantic_gate"


def test_semantic_demand_interpreter_rejects_deliverable_as_semantic_identifier() -> None:
    service = SemanticDemandInterpreterService(
        reasoner=_Reasoner(
            _candidate(
                {
                    "truth_claim_required": False,
                    "required_downstream_uses": ["analysis report"],
                    "required_use_safety": {"safe_for_": ["analysis report"]},
                    "required_semantic_properties": {"analysis report": ["readonly"]},
                    "base_constraints": ["output_validation"],
                    "risk_constraints": [],
                    "confidence": 0.9,
                    "rationale": "Malformed fixture.",
                }
            )
        )
    )

    result = service.interpret(
        source_payload=_source_payload(),
        semantic_graph=_source_payload()["semantic_intent_graph"],
        vocabulary=_vocabulary(),
    )

    assert result["status"] == "insufficient_evidence"
    assert result["reason_code"] == "SEMANTIC_DEMAND_DOWNSTREAM_USE_UNGOVERNED"


def test_semantic_demand_interpreter_fails_closed_on_unresolved_demand() -> None:
    service = SemanticDemandInterpreterService(
        reasoner=_Reasoner(
            _candidate(
                {
                    "truth_claim_required": False,
                    "required_downstream_uses": [],
                    "required_use_safety": {},
                    "required_semantic_properties": {},
                    "base_constraints": [],
                    "risk_constraints": [],
                    "resolution_status": "unresolved",
                    "unresolved_reason_codes": [
                        "task_semantics_ambiguous"
                    ],
                    "rationale": "Ambiguous request.",
                }
            )
        )
    )

    result = service.interpret(
        source_payload=_source_payload(),
        semantic_graph=_source_payload()["semantic_intent_graph"],
        vocabulary=_vocabulary(),
    )

    assert result["status"] == "insufficient_evidence"
    assert (
        result["reason_code"]
        == "SEMANTIC_DEMAND_INTERPRETATION_UNRESOLVED"
    )
    assert result["unresolved_reason_codes"] == [
        "task_semantics_ambiguous"
    ]


def test_resolved_empty_demand_is_not_blocked_by_legacy_zero_confidence() -> None:
    service = SemanticDemandInterpreterService(
        reasoner=_Reasoner(
            _candidate(
                {
                    "truth_claim_required": False,
                    "required_downstream_uses": [],
                    "required_use_safety": {},
                    "required_semantic_properties": {},
                    "base_constraints": [],
                    "risk_constraints": [],
                    "confidence": 0.0,
                    "rationale": "No upstream semantic guarantee is required.",
                }
            )
        )
    )

    result = service.interpret(
        source_payload=_source_payload(),
        semantic_graph=_source_payload()["semantic_intent_graph"],
        vocabulary=_vocabulary(),
    )

    assert result["status"] == "accepted"
    assert result["resolution_status"] == "resolved"
    assert result["accepted_requirements"] == {
        "required_downstream_uses": [],
        "required_use_safety": {},
        "required_semantic_properties": {},
        "base_constraints": [],
        "risk_constraints": [],
    }


def _requirements() -> DownstreamPhaseRequirements:
    return DownstreamPhaseRequirements(
        contract_id="compiled_generic",
        consumer_phase_id="consumer",
        operation_type="workspace_analysis_readonly",
        authority_source="compiled_task_semantics",
        allowed_dependency_statuses=["satisfied", "satisfied_with_limitations"],
        required_use_safety={
            "safe_for_downstream_static_analysis": [
                True,
                "true_with_limitations",
            ]
        },
        evidence_required=True,
    )


def _snapshot() -> PhaseDependencySnapshot:
    return PhaseDependencySnapshot(
        dependency_id="dependency",
        producer_task_run_id="producer",
        producer_operation_id="producer_operation",
        producer_phase_id="upstream",
        upstream_result_ref="task_run_result:producer",
        dependency_status="satisfied_with_limitations",
        evidence_refs=["artifact:evidence"],
        limitations=["identity_not_observed"],
        use_safety={
            "safe_for_downstream_static_analysis": "true_with_limitations",
            "safe_for_truth_claim": False,
        },
    )


def test_limitation_resolver_accepts_constraint_bound_compatibility() -> None:
    reasoner = _PayloadReasoner(
        lambda kwargs: {
            "assessments": [
                {
                    "limitation_id": kwargs["payload"]["upstream_context"]
                    ["limitation_bindings"][0]["limitation_id"],
                    "impact": "COMPATIBLE_WITH_CONSTRAINT",
                    "constraints": [
                        "do_not_promote_upstream_identity_to_truth"
                    ],
                    "rationale": "Identity truth is not required.",
                }
            ],
            "confidence": 0.94,
            "rationale": "Compatible with scoped static analysis.",
        }
    )
    service = LimitationCompatibilityResolverService(reasoner=reasoner)

    result = service.resolve(
        requirements=_requirements(),
        snapshot=_snapshot(),
        limitations=["identity_not_observed"],
    )
    assert result["status"] == "accepted"
    assessment = result["assessments"]["identity_not_observed"]
    assert assessment["impact"] == "COMPATIBLE_WITH_CONSTRAINT"
    assert assessment["constraints"] == [
        "do_not_promote_upstream_identity_to_truth"
    ]
    payload = reasoner.last_kwargs["payload"]
    bindings = payload["upstream_context"]["limitation_bindings"]
    frozen_requirements = payload["frozen_downstream_requirements"]
    assert "requirement_provenance" not in frozen_requirements
    assert "source_plan_id" not in frozen_requirements
    assert "source_execution_id" not in frozen_requirements
    assert "source_semantics_sha256" not in frozen_requirements
    assert bindings[0]["description"] == "identity_not_observed"
    assert bindings[0]["limitation_id"].startswith("lim_")
    assert "limitations" not in payload["upstream_context"]
    assessment_schema = payload["output_schema"]["assessments"]
    assert assessment_schema["required_count"] == 1
    assert assessment_schema["item"]["limitation_id"]["enum"] == [
        bindings[0]["limitation_id"]
    ]
    assert "one_supplied_limitation_id" not in str(payload["output_schema"])


def test_limitation_resolver_requires_complete_limitation_coverage() -> None:
    service = LimitationCompatibilityResolverService(
        reasoner=_Reasoner(
            _candidate(
                {
                    "assessments": [],
                    "confidence": 0.92,
                    "rationale": "Incomplete on purpose.",
                }
            )
        )
    )

    result = service.resolve(
        requirements=_requirements(),
        snapshot=_snapshot(),
        limitations=["identity_not_observed"],
    )

    assert result["status"] == "insufficient_evidence"
    assert result["reason_code"] == "LIMITATION_COMPATIBILITY_COVERAGE_REQUIRED"



def test_limitation_resolver_rejects_unknown_opaque_binding() -> None:
    reasoner = _PayloadReasoner(
        lambda _kwargs: {
            "assessments": [
                {
                    "limitation_id": "lim_not_supplied",
                    "impact": "COMPATIBLE",
                    "constraints": [],
                    "rationale": "Unknown binding should be rejected.",
                }
            ],
            "confidence": 0.9,
            "rationale": "Unknown binding fixture.",
        }
    )
    service = LimitationCompatibilityResolverService(reasoner=reasoner)

    result = service.resolve(
        requirements=_requirements(),
        snapshot=_snapshot(),
        limitations=["identity_not_observed"],
    )

    assert result["status"] == "insufficient_evidence"
    assert result["reason_code"] == "LIMITATION_COMPATIBILITY_BINDING_INVALID"


def test_limitation_resolver_rejects_duplicate_opaque_binding() -> None:
    def _duplicate(kwargs):
        binding_id = kwargs["payload"]["upstream_context"][
            "limitation_bindings"
        ][0]["limitation_id"]
        return {
            "assessments": [
                {
                    "limitation_id": binding_id,
                    "impact": "COMPATIBLE",
                    "constraints": [],
                    "rationale": "First assessment.",
                },
                {
                    "limitation_id": binding_id,
                    "impact": "COMPATIBLE",
                    "constraints": [],
                    "rationale": "Duplicate assessment.",
                },
            ],
            "confidence": 0.9,
            "rationale": "Duplicate binding fixture.",
        }

    service = LimitationCompatibilityResolverService(
        reasoner=_PayloadReasoner(_duplicate)
    )

    result = service.resolve(
        requirements=_requirements(),
        snapshot=_snapshot(),
        limitations=["identity_not_observed", "metadata_incomplete"],
    )

    assert result["status"] == "insufficient_evidence"
    assert result["reason_code"] == "LIMITATION_COMPATIBILITY_BINDING_INVALID"


def test_semantic_demand_interpreter_rejects_invalid_use_safety_state() -> None:
    service = SemanticDemandInterpreterService(
        reasoner=_Reasoner(
            _candidate(
                {
                    "truth_claim_required": False,
                    "required_downstream_uses": [],
                    "required_use_safety": {
                        "safe_for_downstream_static_analysis": ["readonly_analysis"]
                    },
                    "required_semantic_properties": {},
                    "base_constraints": [],
                    "risk_constraints": [],
                    "confidence": 0.88,
                    "rationale": "Invalid state fixture.",
                }
            )
        )
    )

    result = service.interpret(
        source_payload=_source_payload(),
        semantic_graph=_source_payload()["semantic_intent_graph"],
        vocabulary=_vocabulary(),
    )

    assert result["status"] == "insufficient_evidence"
    assert result["reason_code"] == "SEMANTIC_DEMAND_USE_SAFETY_STATE_INVALID"


def test_semantic_demand_interpreter_rejects_capability_reclassified_as_constraint() -> None:
    service = SemanticDemandInterpreterService(
        reasoner=_Reasoner(
            _candidate(
                {
                    "truth_claim_required": False,
                    "required_downstream_uses": [],
                    "required_use_safety": {},
                    "required_semantic_properties": {},
                    "base_constraints": ["require_read_workspace"],
                    "risk_constraints": [],
                    "confidence": 0.88,
                    "rationale": "Capability should stay a capability.",
                }
            )
        )
    )

    result = service.interpret(
        source_payload=_source_payload(),
        semantic_graph=_source_payload()["semantic_intent_graph"],
        vocabulary=_vocabulary(),
    )

    assert result["status"] == "insufficient_evidence"
    assert (
        result["reason_code"]
        == "SEMANTIC_DEMAND_CONSTRAINT_RECLASSIFIES_CAPABILITY"
    )


def test_semantic_demand_interpreter_rejects_false_as_required_safety_state() -> None:
    service = SemanticDemandInterpreterService(
        reasoner=_Reasoner(
            _candidate(
                {
                    "truth_claim_required": False,
                    "required_downstream_uses": [],
                    "required_use_safety": {
                        "safe_for_downstream_static_analysis": [False]
                    },
                    "required_semantic_properties": {},
                    "base_constraints": [],
                    "risk_constraints": [],
                    "confidence": 0.88,
                    "rationale": "Unsafe state is not a safety requirement.",
                }
            )
        )
    )

    result = service.interpret(
        source_payload=_source_payload(),
        semantic_graph=_source_payload()["semantic_intent_graph"],
        vocabulary=_vocabulary(),
    )

    assert result["status"] == "insufficient_evidence"
    assert result["reason_code"] == "SEMANTIC_DEMAND_USE_SAFETY_STATE_INVALID"
