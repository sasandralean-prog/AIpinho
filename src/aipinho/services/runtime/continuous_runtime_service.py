from __future__ import annotations

from aipinho.schemas.runtime.continuous_runtime import (
    ContinuousRuntimeCheckpoint,
    ContinuousRuntimeCycle,
    ContinuousRuntimeResume,
)
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.services.runtime.evidence_engine_service import EvidenceEngineService


class ContinuousRuntimeService:
    def __init__(self, evidence: EvidenceEngineService | None = None) -> None:
        self.evidence = evidence or EvidenceEngineService()

    def evaluate(self, run: TaskRun, *, objective: str | None = None) -> ContinuousRuntimeCycle:
        cycle = ContinuousRuntimeCycle(
            run_id=run.run_id,
            objective=objective or self._objective_from_run(run),
            metadata_sanitized={
                "task_status": run.status,
                "operation_type": run.operation_type,
                "contract_type": run.contract_type,
                "runtime_profile": run.runtime_profile,
            },
        )
        self._add_checkpoint(cycle, "objective", "continue", f"Objective accepted for run {run.run_id}.")
        self._add_checkpoint(cycle, "plan", "continue", f"Plan status is {run.plan.status}.")
        if run.status == "waiting_input" and run.approval_id:
            cycle.status = "needs_approval"
            cycle.current_stage = "execution"
            cycle.next_action = "wait_for_approval"
            cycle.reason_code = "approval_required"
            cycle.approval_id = run.approval_id
            self._add_checkpoint(cycle, "execution", "needs_approval", "Execution is waiting for approval.")
            return cycle
        if run.status in {"blocked", "failed", "cancelled"}:
            cycle.status = "blocked"
            cycle.current_stage = "observation"
            cycle.next_action = "surface_block_reason"
            cycle.reason_code = run.block_cause.block_reason_code if run.block_cause else (run.blocked_reasons[0] if run.blocked_reasons else run.status)
            cycle.blocked_reason = cycle.reason_code
            self._add_checkpoint(cycle, "observation", "blocked", f"Run cannot continue: {cycle.reason_code}.")
            return cycle
        if run.status == "completed":
            decision, audit = self.evidence.decide_from_task_run(
                run,
                subject="continuous_runtime_conclusion",
                decision="complete",
                required_kinds=["task_run", "task_run_plan", "execution_graph"],
            )
            if audit.status == "passed":
                cycle.status = "completed"
                cycle.current_stage = "conclusion"
                cycle.next_action = "publish_completion"
                cycle.reason_code = "evidence_backed_completion"
                self._add_checkpoint(
                    cycle,
                    "conclusion",
                    "completed",
                    f"Completion accepted with evidence score {decision.evidence_score.score}.",
                )
                return cycle
            cycle.status = "needs_user"
            cycle.current_stage = "observation"
            cycle.next_action = "request_missing_evidence"
            cycle.reason_code = "completion_evidence_missing"
            cycle.needs_user_reason = "Completion evidence is incomplete."
            self._add_checkpoint(cycle, "observation", "needs_user", "Completion requires more evidence.")
            return cycle
        if run.status in {"created", "queued", "running", "partial"}:
            cycle.status = "continue"
            cycle.current_stage = "continuation"
            cycle.next_action = "continue_runtime"
            cycle.reason_code = f"task_status:{run.status}"
            self._add_checkpoint(cycle, "continuation", "continue", f"Run status {run.status} can continue.")
            return cycle
        cycle.status = "needs_user"
        cycle.current_stage = "observation"
        cycle.next_action = "clarify_runtime_state"
        cycle.reason_code = f"unknown_task_status:{run.status}"
        cycle.needs_user_reason = "Runtime status is not recognized."
        self._add_checkpoint(cycle, "observation", "needs_user", f"Unknown status {run.status}.")
        return cycle

    def resume(self, cycle: ContinuousRuntimeCycle) -> ContinuousRuntimeResume:
        return ContinuousRuntimeResume(
            cycle_id=cycle.cycle_id,
            run_id=cycle.run_id,
            status=cycle.status,
            next_action=cycle.next_action,
            current_stage=cycle.current_stage,
            reason_code=cycle.reason_code,
            checkpoint_count=len(cycle.checkpoints),
        )

    def _add_checkpoint(self, cycle: ContinuousRuntimeCycle, stage: str, status: str, summary: str) -> None:
        cycle.checkpoints.append(
            ContinuousRuntimeCheckpoint(
                stage=stage,
                status=status,
                summary=summary,
                evidence_refs=[{"type": "task_run", "ref_id": cycle.run_id}],
            )
        )

    def _objective_from_run(self, run: TaskRun) -> str:
        return run.operation_type or run.contract_type or "governed_runtime_task"
