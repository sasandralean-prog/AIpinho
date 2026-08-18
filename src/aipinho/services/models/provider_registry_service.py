from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.models.model_provider import ModelProvider
from aipinho.utils.yaml_loader import load_yaml_file


class ProviderRegistryService:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "models" / "provider_registry.yaml"
        self._providers: dict[str, ModelProvider] | None = None

    def load(self) -> "ProviderRegistryService":
        data = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        raw_providers = data.get("providers", {}) if isinstance(data.get("providers", {}), dict) else {}
        self._providers = {str(provider_id): ModelProvider(provider_id=str(provider_id), **value) for provider_id, value in raw_providers.items() if isinstance(value, dict)}
        return self

    @property
    def providers(self) -> dict[str, ModelProvider]:
        if self._providers is None:
            self.load()
        return self._providers or {}

    def list_providers(self) -> list[ModelProvider]:
        return [self.providers[key] for key in sorted(self.providers)]

    def get_provider(self, provider_id: str) -> ModelProvider | None:
        return self.providers.get(provider_id)

    def status(self) -> dict[str, object]:
        providers = self.list_providers()
        return {
            "status": "ok" if providers else "degraded",
            "service": "provider_registry",
            "providers_registered": len(providers),
            "enabled_providers": [provider.provider_id for provider in providers if provider.enabled],
            "real_inference_enabled": any(provider.enabled and provider.real_inference for provider in providers),
            "auto_load_enabled": any(provider.auto_load_enabled and provider.enabled for provider in providers),
        }
