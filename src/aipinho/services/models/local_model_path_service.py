from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.models.local_model_path import LocalModelPath
from aipinho.utils.yaml_loader import load_yaml_file


class LocalModelPathService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "models" / "local_model_paths.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def allowed_roots(self) -> list[str]:
        roots = self.config.get("model_roots", {}) if isinstance(self.config.get("model_roots", {}), dict) else {}
        configured = roots.get("allowed", []) or self.config.get("allowed_model_roots", []) or []
        return [str(item) for item in configured]

    def blocked_roots(self) -> list[str]:
        roots = self.config.get("model_roots", {}) if isinstance(self.config.get("model_roots", {}), dict) else {}
        configured = roots.get("blocked", []) or self.config.get("blocked_model_roots", []) or []
        return [str(item) for item in configured]

    def validation_policy(self) -> dict[str, object]:
        value = self.config.get("validation", {})
        return value if isinstance(value, dict) else {}

    def list_models(self) -> list[LocalModelPath]:
        raw_models = self.config.get("models", {}) if isinstance(self.config.get("models", {}), dict) else {}
        models = []
        for entry_id, value in raw_models.items():
            if isinstance(value, dict):
                models.append(LocalModelPath(entry_id=str(entry_id), **value))
        return sorted(models, key=lambda item: item.entry_id)

    def get_by_model_id(self, model_id: str) -> LocalModelPath | None:
        for model in self.list_models():
            if model.model_id == model_id:
                return model
        return None

    def status(self) -> dict[str, object]:
        models = self.list_models()
        warnings = []
        for model in models:
            if model.enabled and not model.path:
                warnings.append(f"{model.model_id}:model_path_required")
        return {
            "status": "ok" if not warnings else "degraded",
            "service": "local_model_path",
            "models": [model.model_dump() for model in models],
            "allowed_roots": self.allowed_roots(),
            "blocked_roots": self.blocked_roots(),
            "warnings": warnings,
        }
