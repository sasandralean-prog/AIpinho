from __future__ import annotations

from typing import Any

from aipinho.core.paths import PATHS
from aipinho.services.interpreter.interpreter_service import InterpreterService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.utils.yaml_loader import load_yaml_file


class TaskSpeakerUpdateService:
    """Builds human updates from sanitized TaskRun events without exposing raw payloads."""

    def __init__(
        self,
        runtime: TaskRuntimeService | None = None,
        interpreter: InterpreterService | None = None,
    ) -> None:
        self.runtime = runtime or TaskRuntimeService()
        self.interpreter = interpreter or InterpreterService()
        config_path = PATHS.config_root / "runtime" / "task_speaker_update_policy.yaml"
        self.policy = load_yaml_file(config_path, critical=True, root=config_path.parent)

    def updates(self, run_id: str, *, after_event_id: str | None = None, limit: int = 100) -> dict[str, Any]:
        run = self.runtime.get_run(run_id)
        if run is None:
            raise ValueError("task_run_not_found")
        timeline_reader = getattr(self.runtime, "get_timeline", None)
        timeline = timeline_reader(run_id) if callable(timeline_reader) else None
        truth_reader = getattr(self.runtime, "get_runtime_truth", None)
        truth = truth_reader(run_id) if callable(truth_reader) else None
        events = self.runtime.get_events(run_id)
        events = self._after_cursor(events, after_event_id)
        significant_types = set(self.policy.get("significant_event_types", []) or [])
        significant_statuses = set(self.policy.get("significant_statuses", []) or [])
        selected = [
            event
            for event in events
            if event.type in significant_types or event.status in significant_statuses
        ][-max(1, limit):]
        messages = [self._speaker_message(run, event) for event in selected]
        latest_event_id = events[-1].event_id if events else after_event_id
        terminal = str(run.status) in set(self.policy.get("terminal_task_statuses", []) or [])
        interval = int(self.policy.get("poll_interval_seconds", 5))
        return {
            "status": "ok",
            "run_id": run.run_id,
            "run_status": run.status,
            "messages": messages,
            "has_new_message": bool(messages),
            "latest_event_id": latest_event_id,
            "next_poll_seconds": interval,
            "polling": {
                "enabled": not terminal,
                "recommended_interval_seconds": interval,
                "cursor": latest_event_id,
            },
            "timeline_evidence": {
                "timeline_id": timeline.timeline_id if timeline else None,
                "observable": timeline.observable if timeline else False,
                "terminal_event_id": timeline.completion.terminal_event_id if timeline else None,
                "safe_to_report_success": timeline.completion.safe_to_report_success if timeline else False,
                "gaps": timeline.gaps if timeline else ["timeline_unavailable"],
            },
            "runtime_truth": (
                truth.model_dump(mode="json")
                if hasattr(truth, "model_dump")
                else {
                    "status": None,
                    "safe_to_report_success": False,
                    "reason_code": "runtime_truth_unavailable",
                }
            ),
            "raw_included": False,
        }

    def _after_cursor(self, events: list[Any], cursor: str | None) -> list[Any]:
        if not cursor:
            return events
        for index, event in enumerate(events):
            if event.event_id == cursor:
                return events[index + 1 :]
        return events

    def _speaker_message(self, run: Any, event: Any) -> dict[str, Any]:
        interpreted = self.interpreter.interpret_task_event(run, event)
        by_event = self.policy.get("message_type_by_event", {}) or {}
        by_status = self.policy.get("message_type_by_status", {}) or {}
        message_type = str(by_event.get(event.type) or by_status.get(event.status) or "live_update")
        return {
            "message_id": f"speaker_{event.event_id}",
            "message_type": message_type,
            "text": interpreted["semantic_summary"],
            "status": interpreted["semantic_status"],
            "phase": interpreted["phase"],
            "source_event_ids": [event.event_id],
            "timestamp": event.timestamp,
            "task_id": getattr(run, "task_id", None) or run.run_id,
            "task_run_id": run.run_id,
        }
