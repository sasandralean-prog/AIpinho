from __future__ import annotations

from typing import Any

from aipinho.schemas.artifacts.artifact_trace import ArtifactTraceItem


class ArtifactTraceService:
    def item(self, stage: str, status: str, reason: str = "", *, source: str | None = None, data: dict[str, Any] | None = None) -> ArtifactTraceItem:
        return ArtifactTraceItem(stage=stage, status=status, reason=reason, source=source, data=data or {})

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_trace"}
