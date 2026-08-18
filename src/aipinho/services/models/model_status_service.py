from __future__ import annotations

from aipinho.services.models.model_health_service import ModelHealthService
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.model_runtime_policy_service import ModelRuntimePolicyService
from aipinho.services.models.provider_registry_service import ProviderRegistryService


class ModelStatusService:
    def __init__(
        self,
        registry: ModelRegistryService | None = None,
        providers: ProviderRegistryService | None = None,
        health: ModelHealthService | None = None,
        runtime_policy: ModelRuntimePolicyService | None = None,
    ) -> None:
        self.registry = registry or ModelRegistryService()
        self.providers = providers or ProviderRegistryService()
        self.health = health or ModelHealthService(registry=self.registry)
        self.runtime_policy = runtime_policy or ModelRuntimePolicyService()

    def status(self) -> dict[str, object]:
        registry_status = self.registry.status()
        providers_status = self.providers.status()
        policy = self.runtime_policy.load_policy()
        health = [self.health.health(model.model_id).model_dump() for model in self.registry.runtime_models() if self.health.health(model.model_id)]
        warnings: list[str] = []
        if not self.registry.runtime_models():
            warnings.append("no_runtime_models_registered")
        if policy.chat_auto_use_enabled:
            warnings.append("unexpected_chat_auto_model_use_enabled")
        return {
            "status": "ok" if not warnings else "degraded",
            "service": "model_status",
            "registry": registry_status,
            "providers": providers_status,
            "runtime_policy": policy.model_dump(),
            "health": health,
            "registered_local_models": registry_status.get("registered_local_models", 0),
            "chat_model_use_enabled": bool(policy.chat_auto_use_enabled),
            "role_model_use_enabled": bool(policy.role_pipeline_auto_use_enabled),
            "real_inference_enabled": bool(providers_status.get("real_inference_enabled", False)),
            "warnings": warnings,
        }
