from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.roles.role_model_gate import RoleModelGateDecision, RoleModelGateRequest
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.provider_registry_service import ProviderRegistryService
from aipinho.utils.yaml_loader import load_yaml_file


class RoleModelGateService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None, model_registry: ModelRegistryService | None = None, provider_registry: ProviderRegistryService | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "roles" / "role_model_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.model_registry = model_registry or ModelRegistryService()
        self.provider_registry = provider_registry or ProviderRegistryService()

    def decide(self, request: RoleModelGateRequest) -> RoleModelGateDecision:
        policies = self.config.get("policies", {}) if isinstance(self.config.get("policies", {}), dict) else {}
        defaults = self.config.get("defaults", {}) if isinstance(self.config.get("defaults", {}), dict) else {}
        policy = policies.get(request.model_policy, {}) if isinstance(policies.get(request.model_policy, {}), dict) else {}
        model_id = request.requested_model_id or str(defaults.get("default_model", "stub.default"))
        if model_id.startswith("deterministic_"):
            return RoleModelGateDecision(allowed=True, status="deterministic_only", role_id=request.role_id, model_id=model_id, provider_id="deterministic", real_inference=False, trace=[{"stage": "role_model_gate", "status": "deterministic_only", "reason": "declared_deterministic_fallback"}])
        if policy and not bool(policy.get("enabled", True)):
            return RoleModelGateDecision(allowed=False, status="blocked", role_id=request.role_id, model_id=model_id, provider_id="unknown", real_inference=False, blocked_reasons=["role_model_policy_disabled"], trace=[{"stage": "role_model_gate", "status": "blocked", "reason": "role_model_policy_disabled"}])
        if not policy.get("allow_model", False):
            return RoleModelGateDecision(allowed=False, status="deterministic_only", role_id=request.role_id, model_id=model_id, provider_id="deterministic", real_inference=False, trace=[{"stage": "role_model_gate", "status": "deterministic_only", "reason": request.model_policy}])
        blocked: list[str] = []
        warnings: list[str] = []
        allowed_models = {str(item) for item in policy.get("allowed_models", []) or []}
        if allowed_models and model_id not in allowed_models:
            blocked.append("model_not_allowed_by_role_policy")
        model = self.model_registry.get_model(model_id)
        provider = self.provider_registry.get_provider(model.provider_id) if model else None
        if model is None:
            blocked.append("model_not_found")
        elif not model.enabled:
            blocked.append("model_disabled")
        if provider is None:
            blocked.append("provider_not_found")
        elif not provider.enabled:
            blocked.append("provider_disabled")
        real = bool((model and model.real_inference) or (provider and provider.real_inference) or model_id != "stub.default")
        if real:
            if not bool(policy.get("real_inference", defaults.get("real_inference_allowed_by_default", False))):
                blocked.append("real_inference_not_allowed_by_role_policy")
            if bool(policy.get("manual_only", False)) and not (request.allow_real_inference and request.operator_confirmed):
                blocked.append("manual_real_inference_requires_operator_confirmation")
            if model and model.requires_operator_confirmation and not request.operator_confirmed:
                blocked.append("model_requires_operator_confirmation")
            if not request.allow_real_inference:
                blocked.append("real_inference_not_requested")
        if not request.output_contract and not request.prompt_assembly.get("output_contract"):
            blocked.append("missing_output_contract")
        if not request.safety_envelope and not request.prompt_assembly.get("safety_envelope"):
            blocked.append("missing_safety_envelope")
        blocked = list(dict.fromkeys(blocked))
        provider_id = provider.provider_id if provider else "unavailable"
        return RoleModelGateDecision(
            allowed=not blocked,
            status="allowed" if not blocked else "blocked",
            role_id=request.role_id,
            model_id=model_id,
            provider_id=provider_id,
            real_inference=bool(real and not blocked),
            blocked_reasons=blocked,
            warnings=list(dict.fromkeys(warnings)),
            trace=[{"stage": "role_model_gate", "status": "allowed" if not blocked else "blocked", "reason": ",".join(blocked) or "stub_model_allowed"}],
        )

    def status(self) -> dict[str, object]:
        policies = self.config.get("policies", {}) if isinstance(self.config.get("policies", {}), dict) else {}
        binding_controlled = policies.get("binding_controlled", {}) if isinstance(policies.get("binding_controlled", {}), dict) else {}
        return {"status": "ok", "service": "role_model_gate", "default_model": self.config.get("defaults", {}).get("default_model", "stub.default"), "real_inference_auto_use": bool(binding_controlled.get("real_inference", False)), "silent_stub_fallback": False}
