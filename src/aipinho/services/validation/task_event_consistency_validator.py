from __future__ import annotations
from typing import Any
from aipinho.services.validation.validation_common import as_dict, as_list, finding

class TaskEventConsistencyValidator:
    def validate(self, events: Any) -> list:
        event_list = [as_dict(item) for item in as_list(events)]
        findings = []
        started_steps: set[str] = set()
        completed_steps: set[str] = set()
        terminal_seen = False
        for event in event_list:
            event_type = str(event.get("type") or event.get("event_type") or "")
            step_id = str(event.get("step_id") or "")
            if terminal_seen and event_type.startswith("step_"):
                findings.append(finding("event_order_invalid", "Step event after terminal run", "A step event appears after terminal run event.", severity="error", validator="task_event_consistency", evidence=[event_type], blocking=True))
            if event_type in {"run_completed", "run_partial", "run_failed", "run_cancelled", "run_blocked"}:
                terminal_seen = True
            if event_type == "step_started" and step_id:
                started_steps.add(step_id)
            if event_type in {"step_completed", "step_partial", "step_failed", "step_blocked", "step_cancelled"} and step_id:
                if step_id not in started_steps:
                    findings.append(finding("event_order_invalid", "Step finished before start", f"{step_id} finished before step_started.", severity="error", validator="task_event_consistency", evidence=[step_id], blocking=True))
                if step_id in completed_steps and event_type == "step_completed":
                    findings.append(finding("duplicate_execution_signal", "Duplicate step completion", f"{step_id} has duplicate completion signal.", severity="error", validator="task_event_consistency", evidence=[step_id], blocking=True))
                if event_type == "step_completed":
                    completed_steps.add(step_id)
        return findings

    def status(self): return {"status": "ok", "service": "task_event_consistency_validator"}
