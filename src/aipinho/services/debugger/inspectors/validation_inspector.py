from __future__ import annotations

from aipinho.services.debugger.inspectors._shared import BaseInspector, finding
from aipinho.services.validation.validation_gate_service import ValidationGateService


class ValidationInspector(BaseInspector):
    target_type = "validation"

    def inspect(self, validation_id: str):
        result = ValidationGateService().get_result(validation_id)
        if result is None:
            return self.missing(validation_id)
        data = result.model_dump() if hasattr(result, "model_dump") else result
        findings = []
        if isinstance(data, dict) and data.get("status") in {"failed", "rejected"}:
            findings.append(finding("validation_failed", "Validation result is failed/rejected"))
        return self.result(validation_id, {"validation": data}, findings, summary="Validation inspected")
