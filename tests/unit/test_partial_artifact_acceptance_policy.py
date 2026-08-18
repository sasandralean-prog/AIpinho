from __future__ import annotations

from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    ReadonlyAnalysisArtifactRuntimeService,
)
from aipinho.services.runtime.phase_semantic_completion_policy import PhaseSemanticCompletionPolicy


def _artifact() -> dict[str, object]:
    return {
        "artifact_id": "artifact_partial_inventory",
        "status": "blocked",
        "safe_to_use": False,
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
    }


def test_readonly_completion_uses_semantic_blocker_for_partial_artifact() -> None:
    runtime = ReadonlyAnalysisArtifactRuntimeService()
    decision = PhaseSemanticCompletionPolicy().evaluate(
        phase_id="phase_1",
        phase_kind="discovery",
        runtime_status="blocked",
        validation=_validation(),
        artifacts=[_artifact()],
    )
    validation = runtime._apply_phase_completion_decision(_validation(), decision)  # noqa: SLF001

    completion = runtime._completion(  # noqa: SLF001
        ["reports/example/media_inventory.csv"],
        [_artifact()],
        validation,
        status="blocked",
        phase_decision=decision,
    )

    assert completion.status == "blocked"
    assert completion.safe_to_report_success is False
    assert completion.metadata["reason_code"] == "MUSIC_INVENTORY_PARTIAL_NOT_ACCEPTED_BY_PHASE_CONTRACT"
    assert "TASKRUN_LIFECYCLE_TIMEOUT" not in completion.missing_outcomes
    assert completion.metadata["safe_for_limited_discovery"] is True


def test_limited_policy_forbids_full_inventory_claims() -> None:
    decision = PhaseSemanticCompletionPolicy(partial_inventory_allowed=True).evaluate(
        phase_id="phase_1",
        phase_kind="discovery",
        runtime_status="completed",
        validation=_validation(),
        artifacts=[_artifact()],
    )

    assert decision.status == "completed_with_limitations"
    assert "full_inventory" in decision.forbidden_claims
    assert "firetest_ready" in decision.forbidden_claims
    assert decision.phase_dependency["status"] == "satisfied_with_limitations"
