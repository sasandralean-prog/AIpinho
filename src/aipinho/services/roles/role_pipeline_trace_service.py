from __future__ import annotations

from typing import Any

from aipinho.schemas.roles.role_pipeline_trace import RolePipelineTraceItem


class RolePipelineTraceService:
    def item(self, stage: str, status: str, reason: str = "", *, role_id: str | None = None, pass_id: str | None = None, data: dict[str, Any] | None = None) -> RolePipelineTraceItem:
        return RolePipelineTraceItem(stage=stage, status=status, reason=reason, role_id=role_id, pass_id=pass_id, data=data or {})

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "role_pipeline_trace"}
