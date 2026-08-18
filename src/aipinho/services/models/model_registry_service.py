from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.utils.yaml_loader import load_yaml_file


class ModelRegistryService:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "models" / "model_registry.yaml"
        self._models: dict[str, ModelDefinition] | None = None
        self._runtime_model_ids: set[str] = set()
        self._compat_model_ids: set[str] = set()
        self._config: dict[str, object] | None = None

    def load(self) -> "ModelRegistryService":
        data = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self._config = data
        raw_models = data.get("models", {}) if isinstance(data.get("models", {}), dict) else {}
        raw_compat = data.get("compat_models", {}) if isinstance(data.get("compat_models", {}), dict) else {}
        models: dict[str, ModelDefinition] = {}
        self._runtime_model_ids = set()
        self._compat_model_ids = set()
        for model_id, value in raw_models.items():
            if isinstance(value, dict):
                key = str(model_id)
                models[key] = ModelDefinition(model_id=key, **value)
                self._runtime_model_ids.add(key)
        for model_id, value in raw_compat.items():
            if isinstance(value, dict):
                key = str(model_id)
                models[key] = ModelDefinition(model_id=key, **value)
                self._compat_model_ids.add(key)
        self._models = models
        return self

    @property
    def models(self) -> dict[str, ModelDefinition]:
        if self._models is None:
            self.load()
        return self._models or {}

    def list_models(self) -> list[ModelDefinition]:
        return [self.models[key] for key in sorted(self.models)]

    def get_model(self, model_id: str) -> ModelDefinition | None:
        return self.models.get(model_id)

    def enabled_models(self) -> list[ModelDefinition]:
        return [model for model in self.list_models() if model.enabled]

    def runtime_models(self) -> list[ModelDefinition]:
        self.models
        return [self.models[key] for key in sorted(self._runtime_model_ids) if key in self.models]

    def compat_models(self) -> list[ModelDefinition]:
        self.models
        return [self.models[key] for key in sorted(self._compat_model_ids) if key in self.models]

    def get_runtime_model(self, model_id: str) -> ModelDefinition | None:
        self.models
        if model_id not in self._runtime_model_ids:
            return None
        return self.models.get(model_id)

    def default_coding_candidate(self) -> ModelDefinition | None:
        for model in self.runtime_models():
            if model.default_coding_candidate:
                return model
        return None

    def models_by_capability(self, capability: str) -> list[ModelDefinition]:
        return [model for model in self.runtime_models() if capability in set(model.capabilities)]

    def status(self) -> dict[str, object]:
        models = self.list_models()
        runtime_models = self.runtime_models()
        compat_models = self.compat_models()
        default_coding = self.default_coding_candidate()
        runtime_defaults = (self._config or {}).get("runtime_defaults", {}) if isinstance((self._config or {}).get("runtime_defaults", {}), dict) else {}
        real_inference_enabled = bool(runtime_defaults.get("chat_model_use_enabled", False) or runtime_defaults.get("role_model_use_enabled", False))
        return {
            "status": "ok" if runtime_models else "degraded",
            "service": "model_registry",
            "models_registered": len(models),
            "registered_local_models": len(runtime_models),
            "compat_models_registered": len(compat_models),
            "enabled_models": [model.model_id for model in models if model.enabled],
            "real_inference_enabled": real_inference_enabled,
            "chat_model_use_enabled": bool(runtime_defaults.get("chat_model_use_enabled", False)),
            "role_model_use_enabled": bool(runtime_defaults.get("role_model_use_enabled", False)),
            "default_model": str(runtime_defaults.get("default_model", "stub.default")),
            "default_coding_candidate": default_coding.model_id if default_coding else None,
            "runtime_model_ids": [model.model_id for model in runtime_models],
            "compat_model_ids": [model.model_id for model in compat_models],
        }
