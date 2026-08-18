from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

from aipinho.schemas.runtime.phase_progression import FireTestPhaseProgressionState, PhaseProgressionGate


class PhaseProgressionGateService:
    BLOCKING_STATUSES = {"blocked", "failed", "cancelled", "timeout_blocked"}

    def evaluate(
        self,
        phase: str,
        *,
        prior_states: Iterable[FireTestPhaseProgressionState | dict[str, Any]] = (),
    ) -> PhaseProgressionGate:
        states = [self._state(item) for item in prior_states]
        blocking = next((item for item in states if item.status in self.BLOCKING_STATUSES), None)
        previous = states[-1] if states else None
        if blocking is not None:
            reason = blocking.reason_code or blocking.prior_blocking_reason or blocking.skip_reason or blocking.status
            return PhaseProgressionGate(
                phase=phase,
                allowed_to_start=False,
                status="skipped_due_to_prior_block",
                canonical_progression_valid=True,
                prior_phase_status=previous.status if previous else None,
                prior_blocking_phase=blocking.phase,
                prior_blocking_reason=reason,
                skip_reason="skipped_due_to_prior_block",
                reason_code="PHASE_SKIPPED_DUE_TO_PRIOR_BLOCK",
            )
        return PhaseProgressionGate(
            phase=phase,
            allowed_to_start=True,
            status="allowed_to_start",
            canonical_progression_valid=True,
            prior_phase_status=previous.status if previous else None,
        )

    def skipped_state(
        self,
        phase: str,
        *,
        gate: PhaseProgressionGate,
    ) -> FireTestPhaseProgressionState:
        return FireTestPhaseProgressionState(
            phase=phase,
            status="skipped_due_to_prior_block",
            canonical_progression_valid=True,
            prior_phase_status=gate.prior_phase_status,
            prior_blocking_phase=gate.prior_blocking_phase,
            prior_blocking_reason=gate.prior_blocking_reason,
            allowed_to_start=False,
            skip_reason=gate.skip_reason,
            reason_code=gate.reason_code,
            safe_to_report_success=False,
        )

    def invalid_post_block_attempt(
        self,
        phase: str,
        *,
        prior_states: Iterable[FireTestPhaseProgressionState | dict[str, Any]],
        task_run_id: str | None = None,
        result_ref_id: str | None = None,
    ) -> FireTestPhaseProgressionState:
        gate = self.evaluate(phase, prior_states=prior_states)
        return FireTestPhaseProgressionState(
            phase=phase,
            status="invalid_post_block_attempt",
            canonical_progression_valid=False,
            prior_phase_status=gate.prior_phase_status,
            prior_blocking_phase=gate.prior_blocking_phase,
            prior_blocking_reason=gate.prior_blocking_reason,
            allowed_to_start=False,
            skip_reason="phase_called_after_prior_block",
            task_run_id=task_run_id,
            result_ref_id=result_ref_id,
            reason_code="INVALID_POST_BLOCK_ATTEMPT",
            safe_to_report_success=False,
        )

    def run(
        self,
        phases: Iterable[str],
        executor: Callable[[str], FireTestPhaseProgressionState | dict[str, Any]],
    ) -> list[FireTestPhaseProgressionState]:
        states: list[FireTestPhaseProgressionState] = []
        for phase in phases:
            gate = self.evaluate(phase, prior_states=states)
            if not gate.allowed_to_start:
                states.append(self.skipped_state(phase, gate=gate))
                continue
            state = self._state(executor(phase))
            states.append(state)
        return states

    def _state(self, value: FireTestPhaseProgressionState | dict[str, Any]) -> FireTestPhaseProgressionState:
        if isinstance(value, FireTestPhaseProgressionState):
            return value
        return FireTestPhaseProgressionState.model_validate(value)
