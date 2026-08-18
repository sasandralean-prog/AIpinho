from __future__ import annotations


class PatchAuditService:
    def audit(self, event_type: str, *, plan_id: str = "", status: str = "ok") -> dict[str, object]:
        return {"event_type": event_type, "plan_id": plan_id, "status": status, "apply_executed": False, "workspace_write": False}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "patch_audit", "apply_logging_enabled": False}
