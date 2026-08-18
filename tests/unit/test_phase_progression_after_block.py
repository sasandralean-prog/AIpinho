from aipinho.schemas.runtime.phase_progression import FireTestPhaseProgressionState
from aipinho.services.runtime.phase_progression_gate_service import PhaseProgressionGateService


def test_phase_progression_marks_later_phases_skipped_after_semantic_block() -> None:
    called: list[str] = []

    def executor(phase: str) -> FireTestPhaseProgressionState:
        called.append(phase)
        if phase == "phase_1":
            return FireTestPhaseProgressionState(
                phase=phase,
                status="blocked",
                reason_code="MUSIC_INVENTORY_PARTIAL_EVIDENCE",
                safe_to_report_success=False,
            )
        return FireTestPhaseProgressionState(
            phase=phase,
            status="completed",
            safe_to_report_success=True,
        )

    states = PhaseProgressionGateService().run(
        ["phase_1", "phase_2", "phase_3", "phase_4", "phase_5", "phase_6"],
        executor,
    )

    assert called == ["phase_1"]
    assert states[0].status == "blocked"
    assert [state.status for state in states[1:]] == ["skipped_due_to_prior_block"] * 5
    assert all(state.prior_blocking_phase == "phase_1" for state in states[1:])
