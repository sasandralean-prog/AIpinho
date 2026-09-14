from __future__ import annotations

from types import SimpleNamespace

from aipinho.schemas.runtime.runtime_timeline import (
    RuntimeTimeline,
    RuntimeTimelineCompletion,
    RuntimeTimelineEvent,
    RuntimeTimelineValidation,
)
from aipinho.schemas.runtime.task_completion import TaskCompletionEvaluation
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.schemas.semantics.semantic_truth_facet import SemanticTruthFacet
from aipinho.services.runtime.runtime_truth_engine import RuntimeTruthEngine
from aipinho.services.runtime.canonical_operation_state_service import (
    CanonicalOperationStateService,
)


class _SemanticTruthStub:
    def __init__(self, facet: SemanticTruthFacet) -> None:
        self.facet = facet

    def evaluate(self, _run):
        return self.facet


def _facet(
    status: str,
    *,
    safe: bool,
    reasons=None,
    disclosures=None,
) -> SemanticTruthFacet:
    return SemanticTruthFacet(
        facet_id=f"semantic_truth_facet_{status}",
        status=status,
        safe_to_report_success=safe,
        semantic_graph_id=(
            None
            if status == "not_applicable"
            else "semantic_graph_fixture"
        ),
        semantic_graph_authority_sha256=(
            None
            if status == "not_applicable"
            else "graph_sha_fixture"
        ),
        reason_codes=list(reasons or []),
        disclosures=list(disclosures or []),
        authority_sha256=f"facet_sha_{status}",
    )


def _run(*, status: str = "completed"):
    return SimpleNamespace(
        status=status,
        task_id="task_semantic_truth",
        run_id="task_run_semantic_truth",
        operation_id="operation_semantic_truth",
        workflow=SimpleNamespace(
            status=status,
            workflow_id="workflow_semantic_truth",
            current_phase=None,
        ),
        required_artifacts=[],
        produced_artifacts=[],
        contract_type="semantic_truth_fixture",
        operation_type="semantic_truth_fixture",
        runtime_profile="fixture",
        block_cause=None,
        blocked_reasons=[],
    )


def _result() -> TaskRunResult:
    return TaskRunResult(
        run_id="task_run_semantic_truth",
        status="completed",
        summary="claimed complete",
        completion=TaskCompletionEvaluation(
            status="completed",
            safe_to_report_success=True,
        ),
        validation={
            "validation_id": "validation_semantic_truth",
            "status": "passed",
        },
    )


def _timeline() -> RuntimeTimeline:
    return RuntimeTimeline(
        timeline_id="timeline_semantic_truth",
        task_id="task_semantic_truth",
        task_run_id="task_run_semantic_truth",
        status="completed",
        events=[
            RuntimeTimelineEvent(
                event_id="event_terminal",
                sequence=1,
                timestamp="2026-09-14T00:00:00+00:00",
                task_id="task_semantic_truth",
                task_run_id="task_run_semantic_truth",
                event_type="run_completed",
                status="completed",
            )
        ],
        validations=[
            RuntimeTimelineValidation(
                validation_id="validation_semantic_truth",
                status="passed",
            )
        ],
        completion=RuntimeTimelineCompletion(
            status="completed",
            safe_to_report_success=True,
            terminal_event_id="event_terminal",
        ),
    )


def _engine(facet: SemanticTruthFacet) -> RuntimeTruthEngine:
    return RuntimeTruthEngine(
        semantic_truth=_SemanticTruthStub(facet)
    )


def test_semantic_blocked_blocks_completed_runtime_truth() -> None:
    truth = _engine(
        _facet(
            "blocked",
            safe=False,
            reasons=["SEMANTIC_TRUTH_REQUIRED_RELATION_BLOCKED"],
        )
    ).evaluate(_run(), result=_result(), timeline=_timeline())

    assert truth.status == "blocked"
    assert truth.safe_to_report_success is False
    assert truth.reason_code == "semantic_truth_blocked"
    assert truth.semantic_truth_status == "blocked"
    assert (
        "completion_completed_semantic_truth_blocked"
        in truth.contradictions
    )


def test_semantic_insufficient_evidence_blocks_completed_claim() -> None:
    truth = _engine(
        _facet(
            "insufficient_evidence",
            safe=False,
            reasons=[
                "SEMANTIC_TRUTH_REQUIRED_RELATION_UNRESOLVED"
            ],
        )
    ).evaluate(_run(), result=_result(), timeline=_timeline())

    assert truth.status == "blocked"
    assert truth.safe_to_report_success is False
    assert truth.reason_code == "semantic_truth_insufficient_evidence"
    assert truth.semantic_truth_status == "insufficient_evidence"
    assert (
        "completion_completed_semantic_truth_unresolved"
        in truth.contradictions
    )


def test_semantic_constrained_keeps_completion_but_not_safe_success() -> None:
    truth = _engine(
        _facet(
            "constrained",
            safe=False,
            reasons=["SEMANTIC_TRUTH_SUCCESS_REQUIRES_DISCLOSURE"],
            disclosures=["identity_scope_limited"],
        )
    ).evaluate(_run(), result=_result(), timeline=_timeline())

    assert truth.status == "completed"
    assert truth.safe_to_report_success is False
    assert truth.reason_code == "semantic_truth_constrained"
    assert truth.semantic_truth_status == "constrained"
    assert truth.semantic_truth_disclosures == [
        "identity_scope_limited"
    ]
    assert truth.speaker_truth_status == "evidence_required"


def test_not_applicable_semantic_facet_preserves_legacy_success() -> None:
    truth = _engine(
        _facet(
            "not_applicable",
            safe=True,
            reasons=["semantic_graph_not_present"],
        )
    ).evaluate(_run(), result=_result(), timeline=_timeline())

    assert truth.status == "completed"
    assert truth.safe_to_report_success is True
    assert truth.semantic_truth_status == "not_applicable"
    assert truth.speaker_truth_status == "allowed"


def test_semantic_insufficient_does_not_turn_active_run_into_failure() -> None:
    truth = _engine(
        _facet(
            "insufficient_evidence",
            safe=False,
            reasons=[
                "SEMANTIC_TRUTH_REQUIRED_RELATION_UNRESOLVED"
            ],
        )
    ).evaluate(_run(status="running"), result=None, timeline=None)

    assert truth.status == "running"
    assert truth.safe_to_report_success is False
    assert truth.semantic_truth_status == "insufficient_evidence"


def test_runtime_truth_exposes_semantic_facet_as_evidence() -> None:
    truth = _engine(
        _facet(
            "ready",
            safe=True,
            reasons=["SEMANTIC_TRUTH_READY"],
        )
    ).evaluate(_run(), result=_result(), timeline=_timeline())

    row = next(
        item
        for item in truth.evidence
        if item.evidence_type == "semantic_truth_facet"
    )
    assert row.evidence_id == "semantic_truth_facet_ready"
    assert row.status == "ready"
    assert row.metadata["safe_to_report_success"] is True
    assert row.metadata["semantic_graph_id"] == (
        "semantic_graph_fixture"
    )


def test_constrained_semantic_truth_blocks_canonical_completed_state() -> None:
    run = _run()
    result = _result()
    truth = _engine(
        _facet(
            "constrained",
            safe=False,
            reasons=["SEMANTIC_TRUTH_SUCCESS_REQUIRES_DISCLOSURE"],
            disclosures=["identity_scope_limited"],
        )
    ).evaluate(run, result=result, timeline=_timeline())

    canonical = CanonicalOperationStateService().derive(
        run,
        result=result,
        truth=truth,
        artifacts=[],
    )

    assert canonical.status == "BLOCKED"
    assert canonical.safe_to_report_success is False
    assert canonical.reason_code == "semantic_truth_constrained"


def test_not_applicable_semantic_truth_allows_canonical_completed_state() -> None:
    run = _run()
    result = _result()
    truth = _engine(
        _facet(
            "not_applicable",
            safe=True,
            reasons=["semantic_graph_not_present"],
        )
    ).evaluate(run, result=result, timeline=_timeline())

    canonical = CanonicalOperationStateService().derive(
        run,
        result=result,
        truth=truth,
        artifacts=[],
    )

    assert canonical.status == "COMPLETED"
    assert canonical.safe_to_report_success is True
