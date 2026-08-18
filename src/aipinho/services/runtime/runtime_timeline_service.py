from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from aipinho.schemas.runtime.runtime_timeline import (
    RuntimeTimeline,
    RuntimeTimelineArtifact,
    RuntimeTimelineCompletion,
    RuntimeTimelineEvent,
    RuntimeTimelineStep,
    RuntimeTimelineValidation,
)
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_event import TaskRunEvent
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.artifacts.artifact_runtime_service import ArtifactRuntimeService
from aipinho.services.runtime.task_run_store import TaskRunStore


_STEP_FINISH_TYPES = {
    "step_completed",
    "step_partial",
    "step_failed",
    "step_blocked",
    "step_cancelled",
}
_TERMINAL_EVENT_TYPES = {
    "run_completed",
    "run_partial",
    "run_failed",
    "run_cancelled",
    "run_blocked",
}
_TERMINAL_STATUSES = {"completed", "partial", "failed", "blocked", "cancelled", "expired"}


class RuntimeTimelineService:
    """Canonical observable timeline built from governed runtime stores."""

    def __init__(
        self,
        *,
        store: TaskRunStore | None = None,
        artifacts: ArtifactRuntimeService | None = None,
    ) -> None:
        self.store = store or TaskRunStore()
        self.artifacts = artifacts or ArtifactRuntimeService()

    def build(self, run_id: str) -> RuntimeTimeline | None:
        run = self.store.get_run_lightweight(run_id)
        if run is None:
            return None
        events = sorted(self.store.get_events(run_id), key=lambda item: item.sequence)
        result = self.store.get_result(run_id)
        timeline_events = self._events(run, events)
        steps = self._steps(run, events)
        artifact_rows = self._artifact_rows(run, result)
        artifacts = self._artifacts(run, artifact_rows, steps, events)
        validations = self._validations(run, result, events)
        completion = self._completion(run, result, events, validations)
        gaps = self._gaps(run, events, steps, artifacts, validations, completion)
        orphan_event_ids = self._orphan_event_ids(run, events)
        orphan_artifact_ids = [artifact.artifact_id for artifact in artifacts if artifact.orphan]
        sequence_contiguous = [event.sequence for event in events] == list(range(1, len(events) + 1))
        observable = not gaps and sequence_contiguous
        return RuntimeTimeline(
            timeline_id=f"runtime_timeline_{run.run_id}",
            task_id=run.task_id or run.run_id,
            task_run_id=run.run_id,
            operation_id=run.operation_id,
            workspace_id=run.workspace_id,
            project_id=run.project_id,
            status=completion.status,
            phase=run.current_phase or self._phase_from_status(run.status),
            events=timeline_events,
            steps=steps,
            artifacts=artifacts,
            validations=validations,
            completion=completion,
            gaps=gaps,
            orphan_event_ids=orphan_event_ids,
            orphan_artifact_ids=orphan_artifact_ids,
            sequence_contiguous=sequence_contiguous,
            observable=observable,
            speaker_truth_evidence={
                "source": "runtime_timeline",
                "terminal_event_id": completion.terminal_event_id,
                "safe_to_report_success": completion.safe_to_report_success,
                "validation_event_ids": [item.event_id for item in validations if item.event_id],
                "artifact_event_ids": list(dict.fromkeys([item.event_id for item in artifacts if item.event_id])),
                "gaps": gaps,
            },
        )

    def _events(self, run: TaskRun, events: list[TaskRunEvent]) -> list[RuntimeTimelineEvent]:
        return [
            RuntimeTimelineEvent(
                event_id=event.event_id,
                sequence=event.sequence,
                timestamp=event.timestamp,
                task_id=run.task_id or run.run_id,
                task_run_id=run.run_id,
                phase=self._event_phase(run, event),
                runtime_step=event.step_id,
                event_type=event.type,
                status=event.status,
                message=event.message,
                duration_ms=self._event_duration_ms(event),
                metadata=event.metadata,
            )
            for event in events
        ]

    def _steps(self, run: TaskRun, events: list[TaskRunEvent]) -> list[RuntimeTimelineStep]:
        events_by_step: dict[str, list[TaskRunEvent]] = {}
        for event in events:
            if event.step_id:
                events_by_step.setdefault(event.step_id, []).append(event)
        rows: list[RuntimeTimelineStep] = []
        for step in run.plan.steps:
            step_events = sorted(events_by_step.get(step.step_id, []), key=lambda item: item.sequence)
            start = next((event for event in step_events if event.type == "step_started"), None)
            finish = next((event for event in reversed(step_events) if event.type in _STEP_FINISH_TYPES), None)
            gap_reasons: list[str] = []
            if start and not finish and str(run.status) in _TERMINAL_STATUSES:
                gap_reasons.append("step_started_without_terminal_event")
            if finish and not start and finish.type not in {"step_blocked", "step_cancelled"}:
                gap_reasons.append("step_terminal_without_start_event")
            if step.status in {"completed", "partial", "failed", "blocked", "cancelled"} and not finish:
                gap_reasons.append("step_status_terminal_without_finish_event")
            duration = self._duration_ms(start.timestamp if start else step.started_at, finish.timestamp if finish else step.finished_at)
            rows.append(
                RuntimeTimelineStep(
                    step_id=step.step_id,
                    step_type=step.step_type,
                    action=step.action,
                    status=step.status,
                    start_event_id=start.event_id if start else None,
                    finish_event_id=finish.event_id if finish else None,
                    started_at=step.started_at or (start.timestamp if start else None),
                    finished_at=step.finished_at or (finish.timestamp if finish else None),
                    duration_ms=duration,
                    warnings=list(step.warnings),
                    violations=list(step.violations),
                    complete=not gap_reasons and (step.status in {"pending", "running"} or finish is not None or step.status == "skipped"),
                    gap_reasons=gap_reasons,
                )
            )
        return rows

    def _artifact_rows(self, run: TaskRun, result: TaskRunResult | None) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in run.produced_artifacts:
            artifact_id = str(item.get("artifact_id") or "")
            if not artifact_id or artifact_id in seen:
                continue
            rows.append(item)
            seen.add(artifact_id)
        for key in [run.run_id, run.task_id, run.task_run_id]:
            if not key:
                continue
            try:
                candidates = self._artifact_lookup_rows(str(key), limit=500)
            except Exception:
                candidates = []
            for item in candidates:
                artifact_id = str(item.get("artifact_id") or "")
                if not artifact_id or artifact_id in seen:
                    continue
                rows.append(item)
                seen.add(artifact_id)
        for artifact_id in self._artifact_ids_from_result(result):
            if artifact_id in seen:
                continue
            try:
                item = self.artifacts.get(artifact_id)
            except Exception:
                item = None
            rows.append(item or {"artifact_id": artifact_id, "status": "unknown"})
            seen.add(artifact_id)
        return rows

    def _artifact_lookup_rows(self, task_id: str, *, limit: int) -> list[dict[str, Any]]:
        lookup = self.artifacts.by_task(task_id, limit=limit)
        if isinstance(lookup, list):
            return lookup
        return list(getattr(lookup, "artifacts", []) or [])

    def _artifacts(
        self,
        run: TaskRun,
        rows: list[dict[str, Any]],
        steps: list[RuntimeTimelineStep],
        events: list[TaskRunEvent],
    ) -> list[RuntimeTimelineArtifact]:
        step_by_id = {step.step_id: step for step in steps}
        step_by_type = {step.step_type: step for step in steps}
        artifacts: list[RuntimeTimelineArtifact] = []
        for row in rows:
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            provenance = row.get("provenance") if isinstance(row.get("provenance"), dict) else {}
            artifact_id = str(row.get("artifact_id") or "")
            producer = row.get("producer_step") or metadata.get("producer_step") or provenance.get("producer_step")
            event_id = row.get("event_id") or metadata.get("event_id") or provenance.get("event_id")
            if not event_id:
                event_id = self._infer_artifact_event_id(str(producer or ""), steps, events)
            orphan_reasons: list[str] = []
            if not artifact_id:
                orphan_reasons.append("artifact_id_missing")
            if not producer:
                orphan_reasons.append("producer_step_missing")
            if not event_id:
                orphan_reasons.append("producer_event_missing")
            linked_step = step_by_id.get(str(producer or "")) or step_by_type.get(str(producer or ""))
            if producer and not linked_step and not event_id:
                orphan_reasons.append("producer_step_not_found_in_timeline")
            artifact = RuntimeTimelineArtifact(
                artifact_id=artifact_id or "artifact_missing_id",
                logical_path=row.get("logical_path") or metadata.get("logical_path"),
                artifact_type=row.get("artifact_type") or metadata.get("artifact_type"),
                producer_step=str(producer) if producer else None,
                event_id=str(event_id) if event_id else None,
                task_id=row.get("task_id") or metadata.get("task_id") or run.task_id or run.run_id,
                task_run_id=row.get("task_run_id") or metadata.get("task_run_id") or run.run_id,
                validation_status=row.get("validation_status"),
                status=row.get("status"),
                storage_ref=row.get("storage_ref") or row.get("storage_path"),
                orphan=bool(orphan_reasons),
                orphan_reasons=orphan_reasons,
            )
            artifacts.append(artifact)
            if linked_step and artifact_id:
                linked_step.artifacts = list(dict.fromkeys([*linked_step.artifacts, artifact_id]))
        return artifacts

    def _validations(self, run: TaskRun, result: TaskRunResult | None, events: list[TaskRunEvent]) -> list[RuntimeTimelineValidation]:
        rows: list[RuntimeTimelineValidation] = []
        validation_event = next((event for event in reversed(events) if event.type in {"validation_finished", "task_completion_evaluated", "validation_failed"}), None)
        if result and isinstance(result.validation, dict):
            rows.append(
                RuntimeTimelineValidation(
                    validation_id=str(result.validation.get("validation_id")) if result.validation.get("validation_id") else None,
                    event_id=validation_event.event_id if validation_event else None,
                    status=str(result.validation.get("status") or result.validation.get("validation_status") or result.status),
                    inputs={
                        "task_run_id": run.run_id,
                        "task_id": run.task_id or run.run_id,
                        "events_count": len(events),
                    },
                    outputs={
                        "result_status": result.status,
                        "safe_to_display": result.safe_to_display,
                    },
                    result=result.validation,
                )
            )
        elif validation_event is not None:
            rows.append(
                RuntimeTimelineValidation(
                    event_id=validation_event.event_id,
                    status=validation_event.status,
                    inputs={"task_run_id": run.run_id},
                    outputs={},
                    result=validation_event.metadata,
                )
            )
        return rows

    def _completion(
        self,
        run: TaskRun,
        result: TaskRunResult | None,
        events: list[TaskRunEvent],
        validations: list[RuntimeTimelineValidation],
    ) -> RuntimeTimelineCompletion:
        terminal_event = next((event for event in reversed(events) if event.type in _TERMINAL_EVENT_TYPES), None)
        if terminal_event is not None:
            status = self._terminal_status_from_event(terminal_event)
            source = "timeline_terminal_event"
        elif result is not None:
            status = result.status
            source = "result_without_terminal_event"
        else:
            status = str(run.status)
            source = "run_status_without_result"
        missing = []
        completion = result.completion if result is not None else None
        if completion is not None:
            missing = [str(item) for item in getattr(completion, "missing_outcomes", []) or []]
        validation_statuses = {item.status for item in validations}
        validation_ok = not validations or validation_statuses <= {"passed", "completed", "validated", "not_applicable"}
        safe_success = (
            status == "completed"
            and source == "timeline_terminal_event"
            and not missing
            and validation_ok
        )
        return RuntimeTimelineCompletion(
            status=status,
            source=source,
            safe_to_report_success=safe_success,
            terminal_event_id=terminal_event.event_id if terminal_event else None,
            missing_outputs=missing,
            derived_from_event_ids=[event.event_id for event in events if event.type in {"task_completion_evaluated", *_TERMINAL_EVENT_TYPES}],
        )

    def _gaps(
        self,
        run: TaskRun,
        events: list[TaskRunEvent],
        steps: list[RuntimeTimelineStep],
        artifacts: list[RuntimeTimelineArtifact],
        validations: list[RuntimeTimelineValidation],
        completion: RuntimeTimelineCompletion,
    ) -> list[str]:
        gaps: list[str] = []
        if not events:
            gaps.append("timeline_events_missing")
        if [event.sequence for event in events] != list(range(1, len(events) + 1)):
            gaps.append("event_sequence_not_contiguous")
        gaps.extend(f"step:{step.step_id}:{reason}" for step in steps for reason in step.gap_reasons)
        gaps.extend(f"artifact:{artifact.artifact_id}:{reason}" for artifact in artifacts for reason in artifact.orphan_reasons)
        if run.status in _TERMINAL_STATUSES and completion.source != "timeline_terminal_event":
            gaps.append("terminal_run_without_terminal_event")
        if completion.status == "completed" and not validations:
            gaps.append("completed_run_without_validation_record")
        return list(dict.fromkeys(gaps))

    def _orphan_event_ids(self, run: TaskRun, events: list[TaskRunEvent]) -> list[str]:
        step_ids = {step.step_id for step in run.plan.steps}
        return [
            event.event_id
            for event in events
            if event.step_id and event.step_id not in step_ids
        ]

    def _infer_artifact_event_id(
        self,
        producer_step: str,
        steps: list[RuntimeTimelineStep],
        events: list[TaskRunEvent],
    ) -> str | None:
        if not producer_step:
            return None
        for step in steps:
            if producer_step in {step.step_id, step.step_type, step.action}:
                return step.finish_event_id or step.start_event_id
        for event in reversed(events):
            if event.step_id == producer_step:
                return event.event_id
            metadata = event.metadata if isinstance(event.metadata, dict) else {}
            if producer_step in {str(metadata.get("producer_step")), str(metadata.get("step_type")), str(metadata.get("action"))}:
                return event.event_id
        return None

    def _artifact_ids_from_result(self, result: TaskRunResult | None) -> list[str]:
        if result is None:
            return []
        ids: list[str] = []

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                for key, item in value.items():
                    if str(key).endswith("artifact_id") and item:
                        ids.append(str(item))
                    visit(item)
            elif isinstance(value, list):
                for item in value:
                    visit(item)
            elif isinstance(value, str) and re.fullmatch(r"artifact_[a-f0-9]{8,}", value):
                ids.append(value)

        visit(result.outputs)
        return list(dict.fromkeys(ids))

    def _event_phase(self, run: TaskRun, event: TaskRunEvent) -> str | None:
        metadata = event.metadata if isinstance(event.metadata, dict) else {}
        return str(metadata.get("phase") or metadata.get("current_phase") or run.current_phase or self._phase_from_status(event.status))

    def _phase_from_status(self, status: str | None) -> str:
        value = str(status or "unknown")
        if value == "created":
            return "created"
        if value == "queued":
            return "queued"
        if value in _TERMINAL_STATUSES:
            return value
        if value == "running":
            return "running"
        return "unknown"

    def _terminal_status_from_event(self, event: TaskRunEvent) -> str:
        mapping = {
            "run_completed": "completed",
            "run_partial": "partial",
            "run_failed": "failed",
            "run_cancelled": "cancelled",
            "run_blocked": "blocked",
        }
        return mapping.get(event.type, event.status)

    def _event_duration_ms(self, event: TaskRunEvent) -> int | None:
        metadata = event.metadata if isinstance(event.metadata, dict) else {}
        for key in ("duration_ms", "elapsed_ms"):
            value = metadata.get(key)
            if isinstance(value, (int, float)):
                return max(0, int(value))
        return None

    def _duration_ms(self, start: str | None, finish: str | None) -> int | None:
        if not start or not finish:
            return None
        try:
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            finish_dt = datetime.fromisoformat(finish.replace("Z", "+00:00"))
        except Exception:
            return None
        return max(0, int((finish_dt - start_dt).total_seconds() * 1000))
