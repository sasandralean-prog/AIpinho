from __future__ import annotations

from aipinho.schemas.runtime.phase_progression import FireTestPhaseProgressionState
from aipinho.services.runtime.phase_progression_gate_service import PhaseProgressionGateService


def test_progression_harness_stops_calling_after_first_block() -> None:
    called: list[str] = []

    def executor(phase: str) -> FireTestPhaseProgressionState:
        called.append(phase)
        if phase == "phase_3":
            return FireTestPhaseProgressionState(
                phase=phase,
                status="blocked",
                reason_code="PHASE3_EVIDENCE_INSUFFICIENT",
                task_run_id="task_run_phase3",
                result_ref_id="task_run_phase3",
                safe_to_report_success=False,
            )
        return FireTestPhaseProgressionState(
            phase=phase,
            status="completed",
            task_run_id=f"task_run_{phase}",
            result_ref_id=f"task_run_{phase}",
            safe_to_report_success=True,
        )

    states = PhaseProgressionGateService().run(
        ["phase_1", "phase_2", "phase_3", "phase_4", "phase_5", "phase_6"],
        executor,
    )

    assert called == ["phase_1", "phase_2", "phase_3"]
    assert [state.status for state in states] == [
        "completed",
        "completed",
        "blocked",
        "skipped_due_to_prior_block",
        "skipped_due_to_prior_block",
        "skipped_due_to_prior_block",
    ]
    assert all(state.prior_blocking_phase == "phase_3" for state in states[3:])


def test_prior_h1c0_block_skips_phase3_without_public_chat_call() -> None:
    called: list[str] = []
    service = PhaseProgressionGateService()
    states = [
        FireTestPhaseProgressionState(
            phase="phase_1",
            status="blocked",
            reason_code="MUSIC_INVENTORY_SEMANTIC_EVIDENCE_INSUFFICIENT",
            safe_to_report_success=False,
        )
    ]

    gate = service.evaluate("phase_3", prior_states=states)
    if gate.allowed_to_start:
        called.append("phase_3")
    else:
        states.append(service.skipped_state("phase_3", gate=gate))

    assert called == []
    assert states[-1].status == "skipped_due_to_prior_block"
    assert states[-1].prior_blocking_phase == "phase_1"
    assert states[-1].safe_to_report_success is False
