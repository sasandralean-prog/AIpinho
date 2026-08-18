from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.schemas.models.model_provider import ModelProvider
from aipinho.services.models.model_capability_service import ModelCapabilityService
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.provider_registry_service import ProviderRegistryService
from aipinho.utils.yaml_loader import load_yaml_file


class ModelRouteDecision:
    def __init__(self, status: str, model: ModelDefinition | None = None, provider: ModelProvider | None = None, reason: str = "", warnings: list[str] | None = None) -> None:
        self.status = status
        self.model = model
        self.provider = provider
        self.reason = reason
        self.warnings = warnings or []

    def as_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "model_id": self.model.model_id if self.model else None,
            "provider_id": self.provider.provider_id if self.provider else None,
            "reason": self.reason,
            "warnings": self.warnings,
        }


class ModelRouterService:
    def __init__(self, model_registry: ModelRegistryService | None = None, provider_registry: ProviderRegistryService | None = None, capability: ModelCapabilityService | None = None) -> None:
        self.model_registry = model_registry or ModelRegistryService()
        self.provider_registry = provider_registry or ProviderRegistryService()
        self.capability = capability or ModelCapabilityService()
        self.policy = load_yaml_file(PATHS.config_root / "models" / "model_routing_policy.yaml", critical=True, root=PATHS.config_root / "models")
        self.role_bindings = load_yaml_file(PATHS.config_root / "roles" / "role_model_bindings.yaml", critical=True, root=PATHS.config_root / "roles")

    def select_model(self, *, requested_model_id: str | None = None, purpose: str = "chat", role_id: str = "speaker") -> ModelRouteDecision:
        routing = self.policy.get("routing", {}) if isinstance(self.policy.get("routing", {}), dict) else {}
        default_model_id = str(routing.get("default_model_id", "stub.default"))
        explicit_request = requested_model_id if requested_model_id else None
        model_id = explicit_request or self._role_model_id(role_id) or self._default_by_role(role_id) or self._default_by_purpose(purpose) or default_model_id
        model = self.model_registry.get_model(str(model_id))
        if model is None:
            return ModelRouteDecision("blocked", reason="model_not_found", warnings=[str(model_id)])
        provider = self.provider_registry.get_provider(model.provider_id)
        if provider is None:
            return ModelRouteDecision("blocked", model=model, reason="provider_not_found", warnings=[model.provider_id])
        provider_match = self.capability.validate_provider_match(model, provider)
        provider_warnings = [str(item) for item in provider_match.get("warnings", [])]
        if provider_match.get("status") == "blocked":
            return ModelRouteDecision("blocked", model=model, provider=provider, reason="provider_capability_mismatch", warnings=[str(item) for item in provider_match.get("blocked_reasons", [])] + provider_warnings)
        if not model.enabled:
            return ModelRouteDecision("blocked", model=model, provider=provider, reason="model_disabled")
        if not provider.enabled:
            return ModelRouteDecision("blocked", model=model, provider=provider, reason="provider_disabled")
        if model.manual_only:
            return ModelRouteDecision("blocked", model=model, provider=provider, reason="model_manual_only", warnings=provider_warnings)
        if model.model_id != default_model_id:
            if not bool(routing.get("real_inference_enabled", False)):
                return ModelRouteDecision("blocked", model=model, provider=provider, reason="real_inference_disabled_by_policy", warnings=["selected_from_role_binding", *provider_warnings])
            if not bool(routing.get("allow_real_provider_selection", False)):
                return ModelRouteDecision("blocked", model=model, provider=provider, reason="real_provider_selection_disabled", warnings=["selected_from_role_binding", *provider_warnings])
        if model.real_inference or provider.real_inference:
            if not bool(routing.get("real_inference_enabled", False)):
                return ModelRouteDecision("blocked", model=model, provider=provider, reason="real_inference_disabled_by_policy", warnings=provider_warnings)
        if not self.capability.supports(model, purpose=purpose, role_id=role_id):
            return ModelRouteDecision("blocked", model=model, provider=provider, reason="model_capability_or_role_mismatch")
        return ModelRouteDecision("ok", model=model, provider=provider, reason="model_selected", warnings=provider_warnings)

    def _role_model_id(self, role_id: str) -> str | None:
        bindings = self.role_bindings.get("role_model_bindings", {}) if isinstance(self.role_bindings.get("role_model_bindings", {}), dict) else {}
        binding = bindings.get(role_id)
        if not isinstance(binding, dict) or not bool(binding.get("enabled", True)):
            return None
        primary = str(binding.get("primary_model") or "")
        return primary or None

    def _default_by_role(self, role_id: str) -> str | None:
        routing = self.policy.get("routing", {}) if isinstance(self.policy.get("routing", {}), dict) else {}
        values: Any = routing.get("default_by_role", {})
        return str(values.get(role_id)) if isinstance(values, dict) and values.get(role_id) else None

    def _default_by_purpose(self, purpose: str) -> str | None:
        routing = self.policy.get("routing", {}) if isinstance(self.policy.get("routing", {}), dict) else {}
        values: Any = routing.get("default_by_purpose", {})
        return str(values.get(purpose)) if isinstance(values, dict) and values.get(purpose) else None

    def status(self) -> dict[str, object]:
        decision = self.select_model()
        routing = self.policy.get("routing", {}) if isinstance(self.policy.get("routing", {}), dict) else {}
        return {"status": "ok" if decision.status == "ok" else "degraded", "service": "model_router", "default": decision.as_dict(), "real_inference_enabled": bool(routing.get("real_inference_enabled", False))}
