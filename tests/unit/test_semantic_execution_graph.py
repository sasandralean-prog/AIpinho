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
from aipinho.services.semantics.semantic_execution_graph_authority_service import (
    SemanticExecutionGraphAuthorityService,
)
from aipinho.services.semantics.semantic_execution_graph_compiler_service import (
    SemanticExecutionGraphCompilerService,
)
from aipinho.services.semantics.task_semantic_vocabulary_compiler_service import (
    TaskSemanticVocabularyCompilerService,
)


def _run(*, steps: list[CanonicalExecutionStep]):
    canonical = CanonicalExecutionPlan(
        semantic_goal="perform a governed multi-step task",
        operation_kind="generic_workflow",
        execution_steps=steps,
        required_capabilities=list(
            dict.fromkeys(
                capability
                for step in steps
                for capability in step.required_capabilities
            )
        ),
        rollback_strategy={"required": False},
        trace_id="trace_semantic_graph",
        metadata={"semantic_intent_graph": {"knowledge_output": True}},
    )
    plan = TaskRunPlan(
        plan_id="plan_semantic_graph",
        contract_type="generic_workflow",
        canonical_execution_plan=canonical,
    )
    run = SimpleNamespace(
        run_id="task_run_semantic_graph",
        task_id="task_semantic_graph",
        plan=plan,
        intent_map={},
        capabilities_required=list(canonical.required_capabilities),
    )
    compiled = TaskSemanticVocabularyCompilerService().compile_for_run(run=run)
    assert compiled.status == "compiled"
    assert compiled.vocabulary is not None
    plan.task_semantic_vocabulary = compiled.vocabulary
    return run


def _step(
    step_id: str,
    *,
    capability: str,
    depends_on: list[str] | None = None,
    work_modes: list[str] | None = None,
):
    return CanonicalExecutionStep(
        step_id=step_id,
        step_type="generic",
        action=step_id,
        side_effect=False,
        depends_on=list(depends_on or []),
        required_capabilities=[capability],
        metadata={"work_modes": list(work_modes or [])},
    )


def test_structural_graph_does_not_invent_linear_edges() -> None:
    run = _run(
        steps=[
            _step("inspect_a", capability="read_workspace"),
            _step("inspect_b", capability="read_workspace"),
            _step("summarize", capability="reporting"),
        ]
    )

    result = SemanticExecutionGraphCompilerService().compile_structural_for_run(
        run=run
    )

    assert result.status == "accepted"
    assert result.graph is not None
    assert len(result.graph.work_units) == 3
    assert result.graph.edges == []
    assert result.graph.status == "partial"


def test_structural_graph_preserves_only_explicit_dependencies() -> None:
    run = _run(
        steps=[
            _step("observe", capability="read_workspace"),
            _step(
                "validate",
                capability="validation",
                depends_on=["observe"],
            ),
            _step("independent_report", capability="reporting"),
        ]
    )

    result = SemanticExecutionGraphCompilerService().compile_structural_for_run(
        run=run
    )

    assert result.graph is not None
    assert len(result.graph.edges) == 1
    edge = result.graph.edges[0]
    producer = next(
        unit for unit in result.graph.work_units
        if "observe" in unit.source_step_ids
    )
    consumer = next(
        unit for unit in result.graph.work_units
        if "validate" in unit.source_step_ids
    )
    assert edge.producer_work_unit_id == producer.work_unit_id
    assert edge.consumer_work_unit_id == consumer.work_unit_id
    assert edge.relation == "ordering_constraint"


def test_explicit_work_modes_make_structural_graph_ready() -> None:
    run = _run(
        steps=[
            _step(
                "observe",
                capability="read_workspace",
                work_modes=["observation"],
            ),
            _step(
                "report",
                capability="reporting",
                work_modes=["reporting"],
            ),
        ]
    )

    result = SemanticExecutionGraphCompilerService().compile_structural_for_run(
        run=run
    )

    assert result.graph is not None
    assert result.graph.status == "ready"
    assert all(
        unit.classification_status == "explicit"
        for unit in result.graph.work_units
    )


def test_candidate_can_group_steps_into_one_semantic_unit() -> None:
    run = _run(
        steps=[
            _step("read_left", capability="read_workspace"),
            _step("read_right", capability="read_workspace"),
            _step(
                "compare",
                capability="analysis",
                depends_on=["read_left", "read_right"],
            ),
        ]
    )
    candidate = SemanticWorkDecompositionCandidate(
        work_units=[
            SemanticWorkUnitCandidate(
                unit_key="observation",
                source_step_ids=["read_left", "read_right"],
                semantic_goal="observe both inputs",
                work_modes=["observation"],
                required_capabilities=["read_workspace"],
            ),
            SemanticWorkUnitCandidate(
                unit_key="comparison",
                source_step_ids=["compare"],
                semantic_goal="compare the observed inputs",
                work_modes=["comparison"],
                required_capabilities=["analysis"],
            ),
        ],
        edges=[
            SemanticDependencyEdgeCandidate(
                producer_unit_key="observation",
                consumer_unit_key="comparison",
                relation="evidence_dependency",
            )
        ],
        confidence=0.9,
        rationale="Two reads form one observation unit feeding comparison.",
    )

    result = SemanticExecutionGraphCompilerService().compile_candidate_for_run(
        run=run,
        candidate=candidate,
    )

    assert result.status == "accepted"
    assert result.graph is not None
    assert result.graph.status == "ready"
    assert len(result.graph.work_units) == 2
    assert len(result.graph.edges) == 1


def test_candidate_rejects_incomplete_step_coverage() -> None:
    run = _run(
        steps=[
            _step("read", capability="read_workspace"),
            _step("report", capability="reporting"),
        ]
    )
    candidate = SemanticWorkDecompositionCandidate(
        work_units=[
            SemanticWorkUnitCandidate(
                unit_key="observation",
                source_step_ids=["read"],
                semantic_goal="observe",
                work_modes=["observation"],
                required_capabilities=["read_workspace"],
            )
        ],
        confidence=0.9,
        rationale="Incomplete by construction.",
    )

    result = SemanticExecutionGraphCompilerService().compile_candidate_for_run(
        run=run,
        candidate=candidate,
    )

    assert result.status == "insufficient_evidence"
    assert (
        result.reason_code
        == "SEMANTIC_WORK_DECOMPOSITION_SOURCE_STEP_COVERAGE_INCOMPLETE"
    )


def test_candidate_rejects_capability_reclassification() -> None:
    run = _run(steps=[_step("read", capability="read_workspace")])
    candidate = SemanticWorkDecompositionCandidate(
        work_units=[
            SemanticWorkUnitCandidate(
                unit_key="observation",
                source_step_ids=["read"],
                semantic_goal="observe",
                work_modes=["observation"],
                required_capabilities=["analysis"],
            )
        ],
        confidence=0.9,
        rationale="Invalid capability substitution.",
    )

    result = SemanticExecutionGraphCompilerService().compile_candidate_for_run(
        run=run,
        candidate=candidate,
    )

    assert result.reason_code == "SEMANTIC_WORK_DECOMPOSITION_CAPABILITY_MISMATCH"


def test_candidate_rejects_ungoverned_work_mode() -> None:
    run = _run(steps=[_step("read", capability="read_workspace")])
    candidate = SemanticWorkDecompositionCandidate(
        work_units=[
            SemanticWorkUnitCandidate(
                unit_key="observation",
                source_step_ids=["read"],
                semantic_goal="observe",
                work_modes=["phase_one_magic"],
                required_capabilities=["read_workspace"],
            )
        ],
        confidence=0.9,
        rationale="Invalid work mode fixture.",
    )

    result = SemanticExecutionGraphCompilerService().compile_candidate_for_run(
        run=run,
        candidate=candidate,
    )

    assert result.reason_code == "SEMANTIC_WORK_DECOMPOSITION_WORK_MODE_UNGOVERNED"


def test_candidate_rejects_cycle() -> None:
    run = _run(
        steps=[
            _step("a", capability="analysis"),
            _step("b", capability="analysis"),
        ]
    )
    candidate = SemanticWorkDecompositionCandidate(
        work_units=[
            SemanticWorkUnitCandidate(
                unit_key="a",
                source_step_ids=["a"],
                semantic_goal="analyze a",
                work_modes=["analysis"],
                required_capabilities=["analysis"],
            ),
            SemanticWorkUnitCandidate(
                unit_key="b",
                source_step_ids=["b"],
                semantic_goal="analyze b",
                work_modes=["analysis"],
                required_capabilities=["analysis"],
            ),
        ],
        edges=[
            SemanticDependencyEdgeCandidate(
                producer_unit_key="a",
                consumer_unit_key="b",
                relation="semantic_dependency",
            ),
            SemanticDependencyEdgeCandidate(
                producer_unit_key="b",
                consumer_unit_key="a",
                relation="semantic_dependency",
            ),
        ],
        confidence=0.9,
        rationale="Cycle fixture.",
    )

    result = SemanticExecutionGraphCompilerService().compile_candidate_for_run(
        run=run,
        candidate=candidate,
    )

    assert result.reason_code == "SEMANTIC_WORK_DECOMPOSITION_CYCLE_DETECTED"


def test_semantic_graph_authority_detects_tampering() -> None:
    run = _run(
        steps=[
            _step(
                "observe",
                capability="read_workspace",
                work_modes=["observation"],
            )
        ]
    )
    result = SemanticExecutionGraphCompilerService().compile_structural_for_run(
        run=run
    )
    assert result.graph is not None
    authority = SemanticExecutionGraphAuthorityService()
    assert authority.verify(result.graph)

    result.graph.work_units[0].semantic_goal = "tampered"
    assert not authority.verify(result.graph)
