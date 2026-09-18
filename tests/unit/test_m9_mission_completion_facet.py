from __future__ import annotations

from aipinho.schemas.runtime.mission_completion import (
    MissionCompletionRequirementEvaluation,
    MissionCompletionSnapshot,
)
from aipinho.services.runtime.mission_completion_facet_service import (
    MissionCompletionFacetService,
)


def _snapshot(*, allow_limited: bool = False, requirements=True):
    return MissionCompletionSnapshot(
        mission_id="mission_facet",
        status="ready",
        source_prompt_sha256="a" * 64,
        strategy="end_to_end_governed",
        completion_requirements=(
            ["validated_change", "promotion_complete"]
            if requirements
            else []
        ),
        validation_requirements=(
            ["tests_pass"] if requirements else []
        ),
        allow_limited_completion=allow_limited,
        task_run_ids=["task_run_a", "task_run_b"],
        terminal_task_run_ids=["task_run_a", "task_run_b"],
        phase_outcome_run_ids=["task_run_a", "task_run_b"],
        phase_outcome_authority_sha256s=["b" * 64, "c" * 64],
        evidence_refs=[
            "task_run:task_run_a",
            "artifact:patch",
            "task_run:task_run_b",
            "evidence:tests",
            "evidence:remote_head",
        ],
        contract_authority_sha256s=["d" * 64],
        contract_revisions=[1],
        authority_sha256="e" * 64,
    )


def _evaluation(
    requirement,
    *,
    kind="completion",
    status="satisfied",
    evidence_ref="artifact:patch",
    producer="task_run_a",
    reason_codes=None,
    limitations=None,
):
    return MissionCompletionRequirementEvaluation(
        requirement=requirement,
        requirement_kind=kind,
        status=status,
        evidence_refs=[evidence_ref] if evidence_ref else [],
        producer_task_run_ids=[producer] if producer else [],
        reason_codes=list(reason_codes or []),
        limitations=list(limitations or []),
    )


def _all_satisfied():
    return [
        _evaluation("validated_change"),
        _evaluation(
            "promotion_complete",
            evidence_ref="evidence:remote_head",
            producer="task_run_b",
        ),
        _evaluation(
            "tests_pass",
            kind="validation",
            evidence_ref="evidence:tests",
            producer="task_run_b",
        ),
    ]


def test_all_required_evidence_resolves_ready_and_safe() -> None:
    facet = MissionCompletionFacetService().evaluate(
        _snapshot(),
        evaluations=_all_satisfied(),
    )

    assert facet.status == "ready"
    assert facet.safe_to_report_success is True
    assert facet.reason_codes == [
        "MISSION_COMPLETION_REQUIREMENTS_SATISFIED"
    ]
    assert set(facet.producer_task_run_ids) == {
        "task_run_a",
        "task_run_b",
    }
    assert len(facet.authority_sha256) == 64


def test_missing_requirement_evaluation_stays_insufficient() -> None:
    facet = MissionCompletionFacetService().evaluate(
        _snapshot(),
        evaluations=_all_satisfied()[:-1],
    )

    assert facet.status == "insufficient_evidence"
    assert facet.safe_to_report_success is False
    assert (
        "MISSION_COMPLETION_EVALUATION_MISSING:validation:tests_pass"
        in facet.reason_codes
    )


def test_limited_evidence_requires_explicit_contract_permission() -> None:
    rows = _all_satisfied()
    rows[1] = _evaluation(
        "promotion_complete",
        status="satisfied_with_limitations",
        evidence_ref="evidence:remote_head",
        producer="task_run_b",
        limitations=["remote_observation_delayed"],
    )

    denied = MissionCompletionFacetService().evaluate(
        _snapshot(allow_limited=False),
        evaluations=rows,
    )
    allowed = MissionCompletionFacetService().evaluate(
        _snapshot(allow_limited=True),
        evaluations=rows,
    )

    assert denied.status == "insufficient_evidence"
    assert denied.safe_to_report_success is False
    assert "MISSION_COMPLETION_LIMITED_NOT_ALLOWED" in denied.reason_codes
    assert allowed.status == "constrained"
    assert allowed.safe_to_report_success is True
    assert "remote_observation_delayed" in allowed.disclosures


def test_blocked_requirement_stays_blocked() -> None:
    rows = _all_satisfied()
    rows[1] = _evaluation(
        "promotion_complete",
        status="blocked",
        evidence_ref=None,
        producer=None,
        reason_codes=["REMOTE_PUSH_NOT_PROVEN"],
    )

    facet = MissionCompletionFacetService().evaluate(
        _snapshot(),
        evaluations=rows,
    )

    assert facet.status == "blocked"
    assert facet.safe_to_report_success is False
    assert facet.reason_codes == ["REMOTE_PUSH_NOT_PROVEN"]


def test_satisfied_evaluation_cannot_reference_evidence_outside_mission() -> None:
    rows = _all_satisfied()
    rows[0] = _evaluation(
        "validated_change",
        evidence_ref="artifact:forged",
        producer="task_run_outside",
    )

    facet = MissionCompletionFacetService().evaluate(
        _snapshot(),
        evaluations=rows,
    )

    assert facet.status == "blocked"
    assert facet.safe_to_report_success is False
    assert (
        "MISSION_COMPLETION_EVIDENCE_OUTSIDE_MISSION:artifact:forged"
        in facet.reason_codes
    )
    assert (
        "MISSION_COMPLETION_PRODUCER_OUTSIDE_MISSION:task_run_outside"
        in facet.reason_codes
    )


def test_facet_hash_is_stable_independent_of_evaluation_order() -> None:
    rows = _all_satisfied()
    service = MissionCompletionFacetService()

    first = service.evaluate(_snapshot(), evaluations=rows)
    second = service.evaluate(
        _snapshot(),
        evaluations=list(reversed(rows)),
    )

    assert first.authority_sha256 == second.authority_sha256
    assert first.model_dump() == second.model_dump()


def test_no_completion_contract_is_not_applicable_and_does_not_lower_truth() -> None:
    facet = MissionCompletionFacetService().evaluate(
        _snapshot(requirements=False),
        evaluations=[],
    )

    assert facet.status == "not_applicable"
    assert facet.safe_to_report_success is True


def test_invalid_snapshot_is_blocked_before_requirement_rows_are_considered() -> None:
    snapshot = _snapshot().model_copy(
        update={
            "status": "invalid",
            "reason_codes": [
                "MISSION_COMPLETION_CONTRACT_IDENTITY_MISMATCH"
            ],
        }
    )

    facet = MissionCompletionFacetService().evaluate(
        snapshot,
        evaluations=_all_satisfied(),
    )

    assert facet.status == "blocked"
    assert facet.safe_to_report_success is False
    assert "MISSION_COMPLETION_SNAPSHOT_INVALID" in facet.reason_codes
