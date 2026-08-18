from __future__ import annotations

from aipinho.schemas.runtime.phase_progression import FireTestPhaseProgressionState
from aipinho.services.runtime.phase_progression_gate_service import PhaseProgressionGateService


def test_phase_progression_allows_first_phase_without_prior_block() -> None:
    gate = PhaseProgressionGateService().evaluate("phase_1", prior_states=[])

    assert gate.allowed_to_start is True
    assert gate.status == "allowed_to_start"
    assert gate.prior_blocking_phase is None


def test_phase_progression_skips_after_prior_block() -> None:
    prior = FireTestPhaseProgressionState(
        phase="phase_1",
        status="blocked",
        reason_code="PHASE_DEPENDENCY_SEMANTIC_INSUFFICIENT",
        safe_to_report_success=False,
    )

    gate = PhaseProgressionGateService().evaluate("phase_2", prior_states=[prior])
    skipped = PhaseProgressionGateService().skipped_state("phase_2", gate=gate)

    assert gate.allowed_to_start is False
    assert skipped.status == "skipped_due_to_prior_block"
    assert skipped.prior_blocking_phase == "phase_1"
    assert skipped.reason_code == "PHASE_SKIPPED_DUE_TO_PRIOR_BLOCK"
    assert skipped.safe_to_report_success is False


def test_invalid_post_block_attempt_is_diagnostic_not_canonical_progression() -> None:
    prior = {"phase": "phase_3", "status": "timeout_blocked", "reason_code": "PUBLIC_RUNTIME_PREACCEPTANCE_BUDGET_EXCEEDED"}

    invalid = PhaseProgressionGateService().invalid_post_block_attempt(
        "phase_4",
        prior_states=[prior],
        task_run_id=None,
        result_ref_id=None,
    )

    assert invalid.status == "invalid_post_block_attempt"
    assert invalid.canonical_progression_valid is False
    assert invalid.prior_blocking_phase == "phase_3"
    assert invalid.reason_code == "INVALID_POST_BLOCK_ATTEMPT"
