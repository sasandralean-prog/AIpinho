from __future__ import annotations

from types import SimpleNamespace

from aipinho.schemas.runtime.mission_completion import MissionCompletionFacet
from aipinho.schemas.runtime.runtime_timeline import (
    RuntimeTimeline,
    RuntimeTimelineCompletion,
    RuntimeTimelineEvent,
    RuntimeTimelineValidation,
)
from aipinho.schemas.runtime.task_completion import TaskCompletionEvaluation
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.schemas.semantics.semantic_truth_facet import SemanticTruthFacet
from aipinho.services.governance.speaker_truth.speaker_truth_service import (
    CanonicalSpeakerTruthService,
)
from aipinho.services.runtime.canonical_operation_state_service import (
    CanonicalOperationStateService,
)
from aipinho.services.runtime.runtime_truth_engine import RuntimeTruthEngine


class _SemanticTruthStub:
    def evaluate(self, _run):
        return SemanticTruthFacet(
            facet_id="semantic_truth_m9_fixture",
            status="ready",
            safe_to_report_success=True,
            semantic_graph_id="semantic_graph_m9_fixture",
            semantic_graph_authority_sha256="a" * 64,
            reason_codes=["SEMANTIC_TRUTH_READY"],
            authority_sha256="b" * 64,
        )


def _run():
    return SimpleNamespace(
        status="completed",
        task_id="task_m9_truth",
        run_id="task_run_m9_truth",
        operation_id="operation_m9_truth",
        workflow=SimpleNamespace(
            status="completed",
            workflow_id="workflow_m9_truth",
            current_phase="final_validation",
        ),
        required_artifacts=[],
        produced_artifacts=[],
        contract_type="m9_truth_fixture",
        operation_type="m9_truth_fixture",
        runtime_profile="fixture",
        block_cause=None,
        blocked_reasons=[],
    )


def _result():
    return TaskRunResult(
        run_id="task_run_m9_truth",
        status="completed",
        summary="local phase completed",
        completion=TaskCompletionEvaluation(
            status="completed",
            safe_to_report_success=True,
        ),
        validation={
            "validation_id": "validation_m9_truth",
            "status": "passed",
        },
    )


def _timeline():
    return RuntimeTimeline(
        timeline_id="timeline_m9_truth",
        task_id="task_m9_truth",
        task_run_id="task_run_m9_truth",
        status="completed",
        phase="final_validation",
        events=[
            RuntimeTimelineEvent(
                event_id="event_m9_terminal",
                sequence=1,
                timestamp="2026-09-18T10:00:00+00:00",
                task_id="task_m9_truth",
                task_run_id="task_run_m9_truth",
                event_type="run_completed",
                status="completed",
            )
        ],
        validations=[
            RuntimeTimelineValidation(
                validation_id="validation_m9_truth",
                status="passed",
            )
        ],
        completion=RuntimeTimelineCompletion(
            status="completed",
            safe_to_report_success=True,
            terminal_event_id="event_m9_terminal",
        ),
    )


def _mission_facet(
    status,
    *,
    safe,
    reasons=None,
    disclosures=None,
):
    return MissionCompletionFacet(
        mission_id="mission_m9_truth",
        snapshot_authority_sha256="c" * 64,
        status=status,
        safe_to_report_success=safe,
        reason_codes=list(reasons or []),
        disclosures=list(disclosures or []),
        authority_sha256="d" * 64,
    )


def _engine():
    return RuntimeTruthEngine(
        semantic_truth=_SemanticTruthStub()  # type: ignore[arg-type]
    )


def test_ready_mission_completion_preserves_completed_runtime_truth() -> None:
    facet = _mission_facet(
        "ready",
        safe=True,
        reasons=["MISSION_COMPLETION_REQUIREMENTS_SATISFIED"],
    )

    truth = _engine().evaluate(
        _run(),
        result=_result(),
        timeline=_timeline(),
        mission_completion=facet,
    )

    assert truth.status == "completed"
    assert truth.safe_to_report_success is True
    assert truth.mission_completion_status == "ready"
    assert truth.mission_completion_authority_sha256 == "d" * 64
    evidence = next(
        item
        for item in truth.evidence
        if item.evidence_type == "mission_completion_facet"
    )
    assert evidence.status == "ready"
    assert evidence.metadata["safe_to_report_success"] is True


def test_insufficient_mission_evidence_caps_local_completion_at_partial() -> None:
    facet = _mission_facet(
        "insufficient_evidence",
        safe=False,
        reasons=["MISSION_COMPLETION_EVALUATION_MISSING:validation:tests_pass"],
    )
    run = _run()
    result = _result()

    truth = _engine().evaluate(
        run,
        result=result,
        timeline=_timeline(),
        mission_completion=facet,
    )
    canonical = CanonicalOperationStateService().derive(
        run,
        result=result,
        truth=truth,
        artifacts=[],
    )
    speaker = CanonicalSpeakerTruthService().from_runtime_truth(truth)

    assert truth.status == "partial"
    assert truth.safe_to_report_success is False
    assert truth.reason_code == "mission_completion_insufficient_evidence"
    assert (
        "mission_completion:MISSION_COMPLETION_EVALUATION_MISSING:validation:tests_pass"
        in truth.missing_evidence
    )
    assert canonical.status == "BLOCKED"
    assert canonical.safe_to_report_success is False
    assert speaker.can_claim_success is False
    assert "completed" in speaker.forbidden_claims


def test_blocked_mission_completion_blocks_runtime_truth() -> None:
    facet = _mission_facet(
        "blocked",
        safe=False,
        reasons=["REMOTE_PUSH_NOT_PROVEN"],
    )

    truth = _engine().evaluate(
        _run(),
        result=_result(),
        timeline=_timeline(),
        mission_completion=facet,
    )

    assert truth.status == "blocked"
    assert truth.safe_to_report_success is False
    assert truth.reason_code == "mission_completion_blocked"
    assert "mission_completion:REMOTE_PUSH_NOT_PROVEN" in truth.missing_evidence


def test_constrained_mission_completion_allows_success_with_disclosure() -> None:
    facet = _mission_facet(
        "constrained",
        safe=True,
        reasons=["MISSION_COMPLETION_READY_WITH_LIMITATIONS"],
        disclosures=["remote_observation_delayed"],
    )

    truth = _engine().evaluate(
        _run(),
        result=_result(),
        timeline=_timeline(),
        mission_completion=facet,
    )
    speaker = CanonicalSpeakerTruthService().from_runtime_truth(truth)

    assert truth.status == "completed"
    assert truth.safe_to_report_success is True
    assert truth.reason_code == "mission_completion_constrained"
    assert speaker.can_claim_success is True
    assert "remote_observation_delayed" in speaker.required_disclosures


def test_not_applicable_mission_completion_preserves_phase_truth() -> None:
    facet = _mission_facet(
        "not_applicable",
        safe=True,
        reasons=["MISSION_COMPLETION_REQUIREMENTS_ABSENT"],
    )

    truth = _engine().evaluate(
        _run(),
        result=_result(),
        timeline=_timeline(),
        mission_completion=facet,
    )

    assert truth.status == "completed"
    assert truth.safe_to_report_success is True
    assert truth.mission_completion_status == "not_applicable"
