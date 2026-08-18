from __future__ import annotations
from aipinho.schemas.validation.validation_audit import ValidationAudit
from aipinho.services.validation.validation_store import ValidationStore

class ValidationAuditService:
    def __init__(self, store: ValidationStore | None = None) -> None:
        self.store = store or ValidationStore()

    def record(self, result) -> ValidationAudit:
        return ValidationAudit(validation_id=result.validation_id, target_type=result.target_type, target_id=result.target_id, status=result.status, reason="validation_gate_result", trace_ref=f"validation/results/{result.validation_id}/trace", warnings=list(result.warnings))

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "validation_audit", "raw_content_enabled": False}
