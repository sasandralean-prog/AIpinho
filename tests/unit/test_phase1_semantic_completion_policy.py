from __future__ import annotations

from aipinho.services.runtime.phase_semantic_completion_policy import PhaseSemanticCompletionPolicy


def _partial_inventory_artifact() -> dict[str, object]:
    return {
        "artifact_id": "artifact_partial_inventory",
        "status": "blocked",
        "safe_to_use": False,
        "selected_rows": 100,
        "bound_rows": 100,
        "evidence_ref_count": 100,
        "metadata": {
            "semantic_contract_status": "partial",
            "reason_code": "MUSIC_INVENTORY_PARTIAL_EVIDENCE",
            "row_evidence_coverage": {"status": "satisfied"},
            "safe_to_use": False,
        },
    }


def _validation() -> dict[str, object]:
    return {
        "status": "blocked",
        "expected_outputs": ["artifact_result", "validation_result", "artifact:media_corpus_inventory"],
        "fulfilled_outputs": ["artifact_result", "validation_result"],
        "missing_outputs": ["artifact:media_corpus_inventory"],
        "blocking_findings": ["TASKRUN_LIFECYCLE_TIMEOUT"],
    }


def test_partial_artifact_not_accepted_by_default_blocks_with_semantic_reason() -> None:
    decision = PhaseSemanticCompletionPolicy().evaluate(
        phase_id="phase_1",
        phase_kind="discovery",
        runtime_status="blocked",
        validation=_validation(),
        artifacts=[_partial_inventory_artifact()],
    )

    assert decision.status == "blocked"
    assert decision.reason_code == "MUSIC_INVENTORY_PARTIAL_NOT_ACCEPTED_BY_PHASE_CONTRACT"
    assert "TASKRUN_LIFECYCLE_TIMEOUT" not in decision.blocking_findings
    assert decision.safe_for_limited_discovery is True
    assert decision.safe_to_report_success is False


def test_partial_artifact_accepted_by_policy_completes_with_limitations() -> None:
    decision = PhaseSemanticCompletionPolicy(partial_inventory_allowed=True).evaluate(
        phase_id="phase_1",
        phase_kind="discovery",
        runtime_status="completed",
        validation=_validation() | {"status": "passed_with_limitations"},
        artifacts=[_partial_inventory_artifact()],
    )

    assert decision.status == "completed_with_limitations"
    assert decision.validation_status == "passed_with_limitations"
    assert decision.partial_artifact_accepted is True
    assert decision.phase_dependency["status"] == "satisfied_with_limitations"
    assert "full_inventory" in decision.forbidden_claims


def test_rows_alone_are_not_sufficient_without_evidence_refs() -> None:
    artifact = _partial_inventory_artifact()
    artifact["evidence_ref_count"] = 0

    decision = PhaseSemanticCompletionPolicy(partial_inventory_allowed=True).evaluate(
        phase_id="phase_1",
        phase_kind="discovery",
        runtime_status="completed",
        validation=_validation(),
        artifacts=[artifact],
    )

    assert decision.status == "blocked"
    assert decision.safe_to_report_success is False
    assert decision.reason_code != "PHASE1_DISCOVERY_COMPLETED_WITH_LIMITED_INVENTORY"
