from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.schemas.roles.role_model_binding import RoleInferenceRequest
from aipinho.utils.yaml_loader import load_yaml_file


class ManualEscalationGateService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "roles" / "manual_escalation_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def decide(self, request: RoleInferenceRequest, model: ModelDefinition | None) -> dict[str, object]:
        policy = self.config.get("manual_escalation", {}) if isinstance(self.config.get("manual_escalation", {}), dict) else {}
        blocked: list[str] = []
        warnings: list[str] = []
        if not model:
            blocked.append("model_not_found")
            return {"allowed": False, "status": "blocked", "blocked_reasons": blocked, "warnings": warnings}
        is_manual = bool(model.manual_only or model.parameter_class == "14b")
        if not is_manual:
            return {"allowed": True, "status": "allowed", "blocked_reasons": blocked, "warnings": warnings}
        if not request.manual_escalation:
            blocked.append("manual_escalation_required")
        if policy.get("require_operator_confirmation", True) and not request.operator_confirmed:
            blocked.append("operator_confirmation_required")
        if policy.get("require_latency_warning_acknowledged", True) and not request.latency_warning_acknowledged:
            blocked.append("latency_warning_acknowledgement_required")
        if policy.get("require_reason", True) and not request.reason:
            blocked.append("manual_escalation_reason_required")
        allowed_manual = {str(item) for item in policy.get("allowed_manual_models", []) or []}
        if model.model_id not in allowed_manual:
            blocked.append("manual_model_not_allowed")
        warnings.append("manual_escalation_model_high_latency") if not blocked else None
        return {"allowed": not blocked, "status": "allowed" if not blocked else "requires_manual_confirmation", "blocked_reasons": blocked, "warnings": warnings}

    def status(self) -> dict[str, object]:
        policy = self.config.get("manual_escalation", {}) if isinstance(self.config.get("manual_escalation", {}), dict) else {}
        return {"status": "ok", "service": "manual_escalation_gate", "enabled": bool(policy.get("enabled", True))}
