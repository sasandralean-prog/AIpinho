from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class ModelInvocationAuditService:
    def build_trace(self, *, stage: str, status: str, reason: str, data: dict[str, Any] | None = None) -> dict[str, object]:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stage": stage,
            "status": status,
            "reason": reason,
            "data": data or {},
        }

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "model_invocation_audit"}
