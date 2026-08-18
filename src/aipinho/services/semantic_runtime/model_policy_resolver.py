from __future__ import annotations

from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.provider_registry_service import ProviderRegistryService


class ModelPolicyResolver:
    def __init__(
        self,
        model_registry: ModelRegistryService | None = None,
        provider_registry: ProviderRegistryService | None = None,
    ) -> None:
        self.model_registry = model_registry or ModelRegistryService()
        self.provider_registry = provider_registry or ProviderRegistryService()

    def evaluate(self, model_id: str, *, manual: bool = False) -> dict[str, object]:
        model = self.model_registry.get_runtime_model(model_id)
        if model is None:
            return {"available": False, "model": None, "provider_id": None, "reasons": ["model_not_registered"]}
        reasons: list[str] = []
        if not model.enabled:
            reasons.append("model_disabled")
        if model.manual_only and not manual:
            reasons.append("manual_only_model_cannot_be_auto_selected")
        provider = self.provider_registry.get_provider(model.provider_id)
        if provider is None:
            reasons.append("provider_not_registered")
        else:
            if not provider.enabled:
                reasons.append("provider_disabled")
        return {
            "available": not reasons,
            "model": model,
            "provider_id": model.provider_id,
            "reasons": reasons,
        }

    def model_satisfies(self, model: ModelDefinition, required: list[str], accepted_tokens: dict[str, set[str]]) -> bool:
        model_set = set(model.capabilities)
        for capability in required:
            token_set = accepted_tokens.get(capability, {capability})
            if capability in model_set or token_set & model_set:
                continue
            return False
        return True
