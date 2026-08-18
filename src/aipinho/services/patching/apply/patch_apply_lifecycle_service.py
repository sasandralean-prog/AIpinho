from __future__ import annotations


class PatchApplyLifecycleService:
    TERMINAL = {"completed", "failed", "blocked", "cancelled", "rolled_back", "failed_with_rollback", "rollback_failed"}

    def is_terminal(self, status: str) -> bool:
        return status in self.TERMINAL

    def can_execute(self, status: str) -> bool:
        return status == "ready_to_execute"

    def can_cancel(self, status: str) -> bool:
        return status not in self.TERMINAL and status != "running"

    def can_rollback(self, status: str) -> bool:
        return status in {"completed", "failed", "failed_with_rollback"}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_apply_lifecycle", "terminal_states": sorted(self.TERMINAL)}
