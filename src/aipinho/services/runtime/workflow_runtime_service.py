from __future__ import annotations

from typing import Any

from aipinho.schemas.events.contracts import utc_now_iso
from aipinho.schemas.runtime.workflow_runtime import (
    WorkflowCheckpoint,
    WorkflowPhase,
    WorkflowPhaseDependency,
    WorkflowResumePoint,
    WorkflowRuntimeInstance,
)


_SUCCESS_STATUSES = {"completed", "partial", "skipped"}
_TERMINAL_STATUSES = {"completed", "partial", "failed", "blocked", "cancelled"}


class WorkflowRuntimeService:
    """Canonical workflow/phase runtime for TaskRun execution state."""

    def create_for_run(self, run: Any) -> WorkflowRuntimeInstance:
        phases: list[WorkflowPhase] = []
        dependencies: list[WorkflowPhaseDependency] = []
        previous_phase_id: str | None = None
        for index, step in enumerate(getattr(run.plan, "steps", []) or [], start=1):
            phase_id = f"phase_{index:03d}_{self._safe_id(step.step_type or step.action)}"
            phase = WorkflowPhase(
                phase_id=phase_id,
                name=str(step.step_type or step.action or phase_id),
                source_step_id=step.step_id,
                source_step_type=str(step.step_type),
                action=str(step.action),
                required=bool(getattr(step, "required", True)),
                depends_on=[previous_phase_id] if previous_phase_id else [],
            )
            phases.append(phase)
            if previous_phase_id:
                dependencies.append(
                    WorkflowPhaseDependency(
                        producer_phase_id=previous_phase_id,
                        consumer_phase_id=phase_id,
                        required_status="completed",
                    )
                )
            previous_phase_id = phase_id
        workflow = WorkflowRuntimeInstance(
            task_id=getattr(run, "task_id", None) or getattr(run, "run_id", None),
            task_run_id=run.run_id,
            operation_id=getattr(run, "operation_id", None),
            runtime_profile=getattr(run, "runtime_profile", None),
            phases=phases,
            dependencies=dependencies,
            finish_contract={
                "phase_validation_required": True,
                "completion_source": "workflow",
                "required_phase_statuses": ["completed", "partial", "skipped"],
            },
        )
        self._refresh(workflow)
        return workflow

    def can_start_phase(self, workflow: WorkflowRuntimeInstance | None, source_step_id: str) -> tuple[bool, list[str]]:
        if workflow is None:
            return True, []
        phase = self.phase_for_step(workflow, source_step_id)
        if phase is None:
            return False, ["workflow_phase_not_found"]
        missing: list[str] = []
        for dependency in workflow.dependencies:
            if dependency.consumer_phase_id != phase.phase_id:
                continue
            producer = self.phase(workflow, dependency.producer_phase_id)
            reasons = self._dependency_missing_reasons(producer, dependency)
            dependency.status = "completed" if not reasons else "missing"
            dependency.missing_reasons = reasons
            missing.extend([f"{dependency.dependency_id}:{reason}" for reason in reasons])
        if missing:
            phase.status = "blocked"
            phase.blocked_reasons = list(dict.fromkeys([*phase.blocked_reasons, "missing_required_phase_dependencies", *missing]))
            workflow.status = "blocked"
            workflow.blocked_reasons = list(dict.fromkeys([*workflow.blocked_reasons, "missing_required_phase_dependencies", *missing]))
            self._checkpoint(workflow, phase, "DEPENDENCY", "blocked", metadata={"missing_reasons": missing})
            self._refresh(workflow)
            return False, list(dict.fromkeys(["missing_required_phase_dependencies", *missing]))
        return True, []

    def start_phase_for_step(
        self,
        workflow: WorkflowRuntimeInstance | None,
        source_step_id: str,
        *,
        event_id: str | None = None,
    ) -> WorkflowRuntimeInstance | None:
        if workflow is None:
            return None
        phase = self.phase_for_step(workflow, source_step_id)
        if phase is None:
            return workflow
        phase.status = "running"
        phase.current_step = "EXECUTION"
        phase.started_at = phase.started_at or utc_now_iso()
        phase.progress = max(phase.progress, 25)
        self._checkpoint(workflow, phase, "START", "completed", event_id=event_id)
        self._checkpoint(workflow, phase, "EXECUTION", "running", event_id=event_id)
        self._refresh(workflow)
        return workflow

    def finish_phase_for_step(
        self,
        workflow: WorkflowRuntimeInstance | None,
        source_step_id: str,
        *,
        status: str,
        event_id: str | None = None,
        artifacts: list[str] | None = None,
        validation_ref: str | None = None,
        violations: list[str] | None = None,
    ) -> WorkflowRuntimeInstance | None:
        if workflow is None:
            return None
        phase = self.phase_for_step(workflow, source_step_id)
        if phase is None:
            return workflow
        phase.produced_artifacts = list(dict.fromkeys([*phase.produced_artifacts, *(artifacts or [])]))
        if validation_ref:
            phase.validation_refs = list(dict.fromkeys([*phase.validation_refs, validation_ref]))
        phase.validation_status = "passed" if status in _SUCCESS_STATUSES and not violations else "failed"
        self._checkpoint(
            workflow,
            phase,
            "VALIDATION",
            phase.validation_status,
            event_id=event_id,
            metadata={"violations": violations or [], "validation_ref": validation_ref},
        )
        if phase.validation_status != "passed":
            phase.status = "blocked" if status == "blocked" else "failed"
            phase.blocked_reasons = list(dict.fromkeys([*phase.blocked_reasons, *(violations or []), "phase_validation_failed"]))
            phase.progress = max(phase.progress, 75)
            self._checkpoint(workflow, phase, "FINISH", phase.status, event_id=event_id)
        else:
            phase.status = "completed" if status == "completed" else status
            phase.progress = 100
            self._checkpoint(workflow, phase, "FINISH", phase.status, event_id=event_id)
        phase.current_step = None
        phase.finished_at = utc_now_iso()
        self._refresh(workflow)
        return workflow

    def resume_point(self, workflow: WorkflowRuntimeInstance | None) -> WorkflowResumePoint | None:
        if workflow is None:
            return None
        for phase in workflow.phases:
            if phase.status in {"pending", "running", "blocked", "failed"}:
                return WorkflowResumePoint(
                    workflow_id=workflow.workflow_id,
                    phase_id=phase.phase_id,
                    source_step_id=phase.source_step_id,
                    status=phase.status,
                    reason="first_non_completed_phase",
                )
        return WorkflowResumePoint(
            workflow_id=workflow.workflow_id,
            phase_id=None,
            source_step_id=None,
            status=workflow.status,
            reason="workflow_terminal",
        )

    def phase_for_step(self, workflow: WorkflowRuntimeInstance, source_step_id: str) -> WorkflowPhase | None:
        return next((phase for phase in workflow.phases if phase.source_step_id == source_step_id), None)

    def phase(self, workflow: WorkflowRuntimeInstance, phase_id: str) -> WorkflowPhase | None:
        return next((phase for phase in workflow.phases if phase.phase_id == phase_id), None)

    def _dependency_missing_reasons(
        self,
        producer: WorkflowPhase | None,
        dependency: WorkflowPhaseDependency,
    ) -> list[str]:
        if producer is None:
            return ["producer_phase_missing"]
        reasons: list[str] = []
        if not producer.required and producer.status in _TERMINAL_STATUSES:
            return []
        if producer.status != dependency.required_status and producer.status not in _SUCCESS_STATUSES:
            reasons.append(f"producer_status:{producer.status}")
        for artifact_id in dependency.required_artifacts:
            if artifact_id not in producer.produced_artifacts:
                reasons.append(f"artifact_missing:{artifact_id}")
        for validation_id in dependency.required_validations:
            if validation_id not in producer.validation_refs and producer.validation_status != "passed":
                reasons.append(f"validation_missing:{validation_id}")
        return reasons

    def _checkpoint(
        self,
        workflow: WorkflowRuntimeInstance,
        phase: WorkflowPhase,
        checkpoint_type: str,
        status: str,
        *,
        event_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> WorkflowCheckpoint:
        checkpoint = WorkflowCheckpoint(
            phase_id=phase.phase_id,
            step_id=phase.source_step_id,
            checkpoint_type=checkpoint_type,
            status=status,
            event_id=event_id,
            metadata=metadata or {},
        )
        phase.checkpoints.append(checkpoint)
        workflow.checkpoints.append(checkpoint)
        workflow.updated_at = checkpoint.timestamp
        return checkpoint

    def _refresh(self, workflow: WorkflowRuntimeInstance) -> None:
        if not workflow.phases:
            workflow.status = "completed"
            workflow.progress = 100
            return
        completed = [phase for phase in workflow.phases if self._phase_satisfied(phase)]
        blocked = [phase for phase in workflow.phases if phase.required and phase.status in {"blocked", "failed"}]
        running = [phase for phase in workflow.phases if phase.status == "running"]
        if blocked:
            workflow.status = "blocked" if any(phase.status == "blocked" for phase in blocked) else "failed"
        elif len(completed) == len(workflow.phases):
            workflow.status = "completed"
        elif running:
            workflow.status = "running"
        else:
            workflow.status = "created"
        current = running[0] if running else next((phase for phase in workflow.phases if phase.status in {"pending", "blocked", "failed"}), None)
        current_index = workflow.phases.index(current) if current in workflow.phases else -1
        previous = workflow.phases[current_index - 1] if current_index > 0 else None
        next_phase = workflow.phases[current_index + 1] if current_index >= 0 and current_index + 1 < len(workflow.phases) else None
        workflow.current_phase = current.phase_id if current else None
        workflow.current_step = current.current_step if current else None
        workflow.previous_phase = previous.phase_id if previous else None
        workflow.next_phase = next_phase.phase_id if next_phase else None
        total = len(workflow.phases) * 100
        achieved = sum(max(0, min(100, phase.progress)) for phase in workflow.phases)
        workflow.progress = int(achieved / total * 100) if total else 100

    def _phase_satisfied(self, phase: WorkflowPhase) -> bool:
        if phase.status in _SUCCESS_STATUSES:
            return True
        return not phase.required and phase.status in _TERMINAL_STATUSES

    def _safe_id(self, value: str) -> str:
        safe = "".join(ch if ch.isalnum() else "_" for ch in str(value).lower()).strip("_")
        return safe or "phase"
