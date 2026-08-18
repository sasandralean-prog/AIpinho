from __future__ import annotations

from typing import Any

from aipinho.schemas.runtime.runtime_timeline import RuntimeTimeline
from aipinho.schemas.runtime.runtime_truth import RuntimeTruth, RuntimeTruthEvidence
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_result import TaskRunResult


_BLOCKING_STATUSES = {"blocked", "failed", "cancelled", "expired"}
_VALIDATION_BAD = {"failed", "blocked", "rejected", "needs_review", "degraded", "incomplete", "missing"}


class RuntimeTruthEngine:
    """Single operational truth resolver for runtime-facing consumers."""

    def evaluate(
        self,
        run: TaskRun,
        *,
        result: TaskRunResult | None = None,
        timeline: RuntimeTimeline | None = None,
    ) -> RuntimeTruth:
        runtime_status = str(run.status)
        workflow_status = str(run.workflow.status) if run.workflow else None
        completion_status = str(result.completion.status) if result and result.completion else (result.status if result else None)
        validation_status = self._validation_status(result, timeline)
        timeline_status = timeline.completion.status if timeline else None
        legacy_result_only = self._legacy_result_only(run, result, timeline)
        evidence = self._evidence(run, result, timeline)
        missing = self._missing_evidence(run, result, timeline, legacy_result_only=legacy_result_only)
        contradictions = self._contradictions(
            runtime_status=runtime_status,
            workflow_status=workflow_status,
            completion_status=completion_status,
            validation_status=validation_status,
            timeline_status=timeline_status,
            timeline=timeline,
            legacy_result_only=legacy_result_only,
        )
        status, reason = self._resolve_status(
            runtime_status=runtime_status,
            workflow_status=workflow_status,
            completion_status=completion_status,
            validation_status=validation_status,
            timeline_status=timeline_status,
            contradictions=contradictions,
            missing=missing,
            result=result,
        )
        safe = (
            status == "completed"
            and not contradictions
            and not missing
            and (bool(timeline and timeline.completion.safe_to_report_success) or legacy_result_only)
            and (workflow_status not in {"blocked", "failed", "cancelled"} or legacy_result_only)
            and validation_status not in _VALIDATION_BAD
        )
        return RuntimeTruth(
            truth_id=f"runtime_truth_{run.run_id}",
            task_id=run.task_id or run.run_id,
            task_run_id=run.run_id,
            status=status,
            phase=self._phase(run, timeline, status),
            reason_code=reason,
            safe_to_report_success=safe,
            runtime_status=runtime_status,
            workflow_status=workflow_status,
            completion_status=completion_status,
            validation_status=validation_status,
            timeline_status=timeline_status,
            ui_status=self._ui_status(status),
            speaker_truth_status="allowed" if safe else "evidence_required",
            evidence=evidence,
            contradictions=contradictions,
            missing_evidence=missing,
        )

    def _resolve_status(
        self,
        *,
        runtime_status: str,
        workflow_status: str | None,
        completion_status: str | None,
        validation_status: str | None,
        timeline_status: str | None,
        contradictions: list[str],
        missing: list[str],
        result: TaskRunResult | None,
    ) -> tuple[str, str]:
        if runtime_status in _BLOCKING_STATUSES:
            return ("cancelled" if runtime_status == "cancelled" else runtime_status, f"runtime_status:{runtime_status}")
        if workflow_status in {"blocked", "failed", "cancelled"}:
            return ("blocked" if workflow_status == "blocked" else workflow_status, f"workflow_status:{workflow_status}")
        if completion_status in {"blocked", "failed", "cancelled"}:
            return ("blocked" if completion_status == "blocked" else completion_status, f"completion_status:{completion_status}")
        if validation_status in _VALIDATION_BAD:
            return ("blocked", f"validation_status:{validation_status}")
        if contradictions:
            return ("blocked", "runtime_truth_contradiction")
        if missing and result is not None and result.status == "completed":
            return ("blocked", "completed_missing_required_evidence")
        if runtime_status in {"created", "queued", "running", "waiting_input", "waiting_delegation"}:
            return (runtime_status, f"runtime_status:{runtime_status}")
        if result is None:
            return (runtime_status, "result_not_available")
        if timeline_status:
            return (timeline_status, f"timeline_status:{timeline_status}")
        return (result.status, f"result_status:{result.status}")

    def _validation_status(self, result: TaskRunResult | None, timeline: RuntimeTimeline | None) -> str | None:
        if result and isinstance(result.validation, dict):
            return str(result.validation.get("status") or result.validation.get("validation_status") or "")
        if timeline and timeline.validations:
            return timeline.validations[-1].status
        if result is None:
            return "not_started"
        return None

    def _evidence(
        self,
        run: TaskRun,
        result: TaskRunResult | None,
        timeline: RuntimeTimeline | None,
    ) -> list[RuntimeTruthEvidence]:
        rows = [
            RuntimeTruthEvidence(evidence_type="task_run", evidence_id=run.run_id, status=str(run.status)),
        ]
        if run.task_id:
            rows.append(RuntimeTruthEvidence(evidence_type="task", evidence_id=run.task_id, status=str(run.status)))
        if run.workflow:
            rows.append(RuntimeTruthEvidence(evidence_type="workflow", evidence_id=run.workflow.workflow_id, status=run.workflow.status))
        if timeline:
            rows.append(RuntimeTruthEvidence(evidence_type="timeline", evidence_id=timeline.timeline_id, status=timeline.status, metadata={"terminal_event_id": timeline.completion.terminal_event_id}))
            rows.extend(
                RuntimeTruthEvidence(
                    evidence_type="artifact",
                    evidence_id=artifact.artifact_id,
                    status=artifact.status,
                    metadata={
                        "logical_path": artifact.logical_path,
                        "producer_step": artifact.producer_step,
                        "event_id": artifact.event_id,
                        "orphan": artifact.orphan,
                        "orphan_reasons": list(artifact.orphan_reasons),
                    },
                )
                for artifact in timeline.artifacts
            )
        if result:
            rows.append(RuntimeTruthEvidence(evidence_type="completion", evidence_id=result.run_id, status=result.status, metadata={"safe_to_display": result.safe_to_display}))
            if isinstance(result.validation, dict):
                rows.append(RuntimeTruthEvidence(evidence_type="validation", evidence_id=str(result.validation.get("validation_id") or ""), status=self._validation_status(result, timeline)))
        return rows

    def _missing_evidence(
        self,
        run: TaskRun,
        result: TaskRunResult | None,
        timeline: RuntimeTimeline | None,
        legacy_result_only: bool = False,
    ) -> list[str]:
        if legacy_result_only:
            return []
        missing: list[str] = []
        if not (run.task_id or run.run_id):
            missing.append("task_id")
        if not run.run_id:
            missing.append("task_run_id")
        if run.workflow is None:
            missing.append("workflow")
        if timeline is None:
            missing.append("timeline")
        elif timeline.completion.status == "completed" and not timeline.completion.terminal_event_id:
            missing.append("timeline_terminal_event")
        if timeline:
            for artifact in timeline.artifacts:
                if artifact.orphan:
                    missing.append(f"artifact:{artifact.artifact_id}:producer_binding")
        if result and result.status == "completed":
            if not result.completion:
                missing.append("completion_evaluation")
            if timeline and not timeline.validations:
                missing.append("validation_evidence")
        return list(dict.fromkeys(missing))

    def _contradictions(
        self,
        *,
        runtime_status: str,
        workflow_status: str | None,
        completion_status: str | None,
        validation_status: str | None,
        timeline_status: str | None,
        timeline: RuntimeTimeline | None,
        legacy_result_only: bool = False,
    ) -> list[str]:
        rows: list[str] = []
        if completion_status == "completed" and runtime_status in _BLOCKING_STATUSES:
            rows.append("completion_completed_runtime_blocking")
        if workflow_status in {"blocked", "failed"} and completion_status == "completed":
            rows.append("completion_completed_workflow_blocking")
        if validation_status in _VALIDATION_BAD and completion_status == "completed":
            rows.append("completion_completed_validation_not_passed")
        if timeline_status in {"blocked", "failed", "cancelled"} and completion_status == "completed":
            rows.append("completion_completed_timeline_blocking")
        if timeline and timeline.gaps and completion_status == "completed" and not legacy_result_only:
            rows.append("completion_completed_timeline_has_gaps")
        if timeline and timeline.orphan_artifact_ids and completion_status == "completed" and not legacy_result_only:
            rows.append("completion_completed_artifact_orphans")
        return list(dict.fromkeys(rows))

    def _legacy_result_only(
        self,
        run: TaskRun,
        result: TaskRunResult | None,
        timeline: RuntimeTimeline | None,
    ) -> bool:
        return bool(
            run.workflow is None
            and result is not None
            and result.status == "completed"
            and result.completion is not None
            and result.completion.safe_to_report_success
            and timeline is not None
            and not timeline.events
        )

    def _phase(self, run: TaskRun, timeline: RuntimeTimeline | None, status: str) -> str:
        if run.workflow and run.workflow.current_phase:
            return run.workflow.current_phase
        if timeline and timeline.phase:
            return timeline.phase
        return status

    def _ui_status(self, status: str) -> str:
        if status == "completed":
            return "completed"
        if status in {"blocked", "failed", "cancelled", "expired"}:
            return status
        if status in {"created", "queued", "running", "waiting_input", "waiting_delegation"}:
            return "active"
        return status or "unknown"
