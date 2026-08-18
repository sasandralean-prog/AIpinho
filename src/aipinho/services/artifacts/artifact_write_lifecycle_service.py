from __future__ import annotations


class ArtifactWriteLifecycleService:
    TERMINAL = {"completed", "failed", "blocked", "cancelled", "invalidated"}
    TRANSITIONS = {
        "created": {"validated", "blocked", "cancelled", "invalidated"},
        "validated": {"ready_to_execute", "blocked", "cancelled", "invalidated"},
        "ready_to_execute": {"running", "cancelled", "invalidated"},
        "running": {"completed", "failed"},
    }

    def can_transition(self, current: str, target: str) -> bool:
        if current in self.TERMINAL:
            return False
        return target in self.TRANSITIONS.get(current, set())

    def ensure(self, current: str, target: str) -> None:
        if not self.can_transition(current, target):
            raise ValueError("invalid_artifact_write_transition")

    def is_terminal(self, status: str) -> bool:
        return status in self.TERMINAL

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_write_lifecycle", "terminal_states": sorted(self.TERMINAL)}
