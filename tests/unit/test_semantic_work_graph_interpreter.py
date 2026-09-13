from __future__ import annotations

from aipinho.schemas.runtime.execution_plan import (
    CanonicalExecutionPlan,
    CanonicalExecutionStep,
)
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.services.semantics.semantic_work_graph_interpreter_service import (
    SemanticWorkGraphInterpreterService,
)
from aipinho.services.semantics.task_semantic_vocabulary_compiler_service import (
    TaskSemanticVocabularyCompilerService,
)


class _Run:
    def __init__(self) -> None:
        self.run_id = "task_run_work_interpreter"
        self.task_id = "task_work_interpreter"
        self.intent_map = {}
        self.capabilities_required = ["read_workspace", "analysis"]
        canonical = CanonicalExecutionPlan(
            semantic_goal="inspect and analyze",
            operation_kind="generic_analysis",
            execution_steps=[
                CanonicalExecutionStep(
                    step_id="inspect",
                    step_type="inspect",
                    action="inspect",
                    required_capabilities=["read_workspace"],
                ),
                CanonicalExecutionStep(
                    step_id="analyze",
                    step_type="analyze",
                    action="analyze",
                    required_capabilities=["analysis"],
                ),
            ],
            required_capabilities=["read_workspace", "analysis"],
            rollback_strategy={"required": False},
            trace_id="trace_work_interpreter",
            metadata={"semantic_intent_graph": {"knowledge_output": True}},
        )
        self.plan = TaskRunPlan(
            plan_id="plan_work_interpreter",
            contract_type="generic_analysis",
            canonical_execution_plan=canonical,
        )
        compiled = TaskSemanticVocabularyCompilerService().compile_for_run(run=self)
        assert compiled.status == "compiled"
        assert compiled.vocabulary is not None
        self.plan.task_semantic_vocabulary = compiled.vocabulary


class _Reasoner:
    def __init__(self, candidate: dict) -> None:
        self.candidate = candidate

    def propose_json(self, **kwargs):
        return {
            "status": "candidate",
            "candidate": self.candidate,
            "model_id": "fixture_model",
            "response_id": "fixture_response",
            "real_inference": False,
            "evaluation_status": "fixture",
            "warnings": [],
        }


def _valid_candidate() -> dict:
    return {
        "work_units": [
            {
                "unit_key": "observation",
                "source_step_ids": ["inspect"],
                "semantic_goal": "inspect evidence",
                "work_modes": ["observation"],
                "required_capabilities": ["read_workspace"],
                "requested_effects": [],
                "prohibited_effects": [],
            },
            {
                "unit_key": "analysis",
                "source_step_ids": ["analyze"],
                "semantic_goal": "analyze evidence",
                "work_modes": ["analysis"],
                "required_capabilities": ["analysis"],
                "requested_effects": [],
                "prohibited_effects": [],
            },
        ],
        "edges": [
            {
                "producer_unit_key": "observation",
                "consumer_unit_key": "analysis",
                "relation": "evidence_dependency",
                "required": True,
            }
        ],
        "confidence": 0.9,
        "rationale": "Observation provides evidence used by analysis.",
    }


def test_interpreter_candidate_remains_subject_to_deterministic_gate() -> None:
    result = SemanticWorkGraphInterpreterService(
        reasoner=_Reasoner(_valid_candidate())
    ).interpret_for_run(run=_Run())

    assert result.status == "accepted"
    assert result.graph is not None
    assert result.graph.status == "ready"
    assert result.provenance["model_id"] == "fixture_model"
    assert result.provenance["authority"] == "deterministic_semantic_graph_gate"


def test_interpreter_cannot_smuggle_ungoverned_work_mode() -> None:
    candidate = _valid_candidate()
    candidate["work_units"][0]["work_modes"] = ["phase_one_magic"]

    result = SemanticWorkGraphInterpreterService(
        reasoner=_Reasoner(candidate)
    ).interpret_for_run(run=_Run())

    assert result.status == "insufficient_evidence"
    assert (
        result.reason_code
        == "SEMANTIC_WORK_DECOMPOSITION_WORK_MODE_UNGOVERNED"
    )


def test_interpreter_cannot_change_capabilities() -> None:
    candidate = _valid_candidate()
    candidate["work_units"][0]["required_capabilities"] = ["analysis"]

    result = SemanticWorkGraphInterpreterService(
        reasoner=_Reasoner(candidate)
    ).interpret_for_run(run=_Run())

    assert result.status == "insufficient_evidence"
    assert (
        result.reason_code
        == "SEMANTIC_WORK_DECOMPOSITION_CAPABILITY_MISMATCH"
    )
