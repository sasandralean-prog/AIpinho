from __future__ import annotations


class ToolPolicyResolver:
    def status(self) -> dict[str, object]:
        return {"status": "ok", "execution_enabled": False, "reason": "Sprint 01 decision-only foundation"}