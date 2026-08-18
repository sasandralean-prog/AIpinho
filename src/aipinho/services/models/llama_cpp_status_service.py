from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.models.llama_cpp_status import LlamaCppStatus
from aipinho.services.models.local_model_path_service import LocalModelPathService
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.models.model_path_validator import ModelPathValidator
from aipinho.services.models.provider_registry_service import ProviderRegistryService
from aipinho.utils.yaml_loader import load_yaml_file


class LlamaCppStatusService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "models" / "llama_cpp_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.paths = LocalModelPathService()
        self.validator = ModelPathValidator(self.paths)
        self.providers = ProviderRegistryService()
        self.models = ModelRegistryService()

    def status(self) -> LlamaCppStatus:
        llama = self.config.get("llama_cpp", {}) if isinstance(self.config.get("llama_cpp", {}), dict) else {}
        provider_id = str(llama.get("provider_id") or "llama_cpp_text")
        provider = self.providers.get_provider(provider_id)
        executable_path = provider.executable_path if provider and provider.executable_path else llama.get("executable_path")
        executable_validation = self.validator.validate_executable_path(executable_path, provider_enabled=bool(provider and provider.enabled))
        runtime_models = [
            model
            for model in self.models.list_models()
            if model.provider_id in set(llama.get("registered_provider_ids", []) or [provider_id])
        ]
        models: list[dict[str, object]] = []
        any_model_configured = False
        any_model_enabled = False
        any_model_valid = False
        for model in runtime_models:
            validation = self.validator.validate_model_path(model.model_path, model_enabled=bool(model.enabled))
            any_model_configured = any_model_configured or bool(model.model_path)
            any_model_enabled = any_model_enabled or bool(model.enabled)
            any_model_valid = any_model_valid or bool(validation.valid)
            models.append({**model.model_dump(), "path_validation": validation.model_dump()})
        warnings: list[str] = []
        blocked: list[str] = []
        if not provider or not provider.enabled or not llama.get("enabled", False):
            blocked.append("provider_disabled")
        if not llama.get("real_inference", False):
            blocked.append("llama_real_inference_disabled")
        if executable_validation.status != "valid":
            warnings.extend(executable_validation.warnings)
            if provider and provider.enabled:
                blocked.extend(executable_validation.blocked_reasons)
        status = "disabled"
        if provider and provider.enabled and llama.get("enabled", False):
            status = "available" if executable_validation.valid and any_model_enabled and any_model_valid else "degraded"
        return LlamaCppStatus(
            provider_id=provider_id,
            enabled=bool(provider and provider.enabled and llama.get("enabled", False)),
            real_inference_enabled=bool(llama.get("real_inference", False)),
            executable_configured=bool(executable_path),
            executable_valid=executable_validation.valid,
            model_configured=any_model_configured,
            model_valid=any_model_valid,
            models=models,
            default_blocked_reasons=list(dict.fromkeys(blocked)),
            warnings=list(dict.fromkeys(warnings)),
            status=status,  # type: ignore[arg-type]
        )
