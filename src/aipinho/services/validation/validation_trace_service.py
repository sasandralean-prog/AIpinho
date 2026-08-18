from __future__ import annotations
from typing import Any
from aipinho.schemas.validation.validation_trace import ValidationTraceItem
from aipinho.services.validation.validation_common import sanitize

class ValidationTraceService:
    def item(self, stage: str, status: str, reason: str, *, rule_id: str | None = None, source: str | None = None, evidence: list[str] | None = None, data: dict[str, Any] | None = None) -> ValidationTraceItem:
        return ValidationTraceItem(stage=stage, status=status, reason=reason, rule_id=rule_id, source=source, evidence=list(evidence or []), data=sanitize(data or {}))

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "validation_trace", "raw_content_enabled": False}
