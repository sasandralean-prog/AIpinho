from __future__ import annotations

from typing import Any

from aipinho.services.interpreter.state_interpreter import StateInterpreter


class InterpreterService:
    def __init__(self, state_interpreter: StateInterpreter | None = None) -> None:
        self.state_interpreter = state_interpreter or StateInterpreter()

    def explain_policy_status(self, status: str) -> str:
        return self.state_interpreter.explain_policy_status(status)

    def interpret_task_event(self, run: Any, event: Any) -> dict[str, object]:
        """Translate one sanitized runtime event into speaker-safe semantics."""
        event_type = str(getattr(event, "type", "task_update"))
        event_status = str(getattr(event, "status", getattr(run, "status", "unknown")))
        summary = str(getattr(event, "message", "") or "Estado operacional atualizado.").strip()
        return {
            "source_event_id": str(getattr(event, "event_id", "")),
            "semantic_summary": summary,
            "semantic_progress": event_type.replace("_", " "),
            "semantic_status": event_status,
            "task_status": str(getattr(run, "status", "unknown")),
            "phase": str(getattr(event, "step_id", "") or event_type),
        }

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "interpreter", "execution_enabled": False}
