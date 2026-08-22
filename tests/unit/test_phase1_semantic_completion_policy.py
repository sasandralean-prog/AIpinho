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


def test_catalog_use_safety_reframes_identity_gap_as_limited_completion() -> None:
    artifact = _partial_inventory_artifact()
    artifact["metadata"]["reason_code"] = "MEDIA_PRIMARY_IDENTITY_EVIDENCE_INSUFFICIENT"
    artifact["metadata"]["inventory_sufficiency_summary"] = {
        "status": "blocked",
        "reason_code": "MEDIA_PRIMARY_IDENTITY_EVIDENCE_INSUFFICIENT",
        "safe_to_use": False,
        "use_safety": {
            "safe_for_truth_claim": False,
            "safe_for_catalog": True,
            "safe_for_planning": "true_with_limitations",
            "safe_for_downstream_static_analysis": "true_with_limitations",
            "safe_for_destructive_action": False,
            "safe_for_user_report": "true_with_limitations",
            "catalog_complete_with_inferred_unknown_status": True,
            "planning_safe_with_limitations": True,
            "limitations": ["observed_identity_truth_claim_insufficient"],
        },
        "coverage_summary": {
            "inventory_confidence": {
                "safe_for_truth_claim": False,
                "safe_for_catalog": True,
                "safe_for_planning": "true_with_limitations",
            }
        },
    }

    decision = PhaseSemanticCompletionPolicy().evaluate(
        phase_id="phase_1",
        phase_kind="discovery",
        runtime_status="blocked",
        validation=_validation(),
        artifacts=[artifact],
    )

    assert decision.status == "completed_with_limitations"
    assert decision.reason_code == "CATALOG_READY_WITH_INFERRED_AND_UNKNOWN_IDENTITY"
    assert decision.safe_to_report_success is False
    assert decision.phase_dependency["artifact_safe_for_truth_claim"] is False
    assert decision.phase_dependency["artifact_safe_for_catalog"] is True
    assert decision.phase_dependency["artifact_safe_for_planning"] == "true_with_limitations"
    assert "full_inventory" in decision.forbidden_claims
