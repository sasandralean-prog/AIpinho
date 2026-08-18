from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.schemas.models.model_runtime_policy import ModelRuntimePolicy
from aipinho.utils.yaml_loader import load_yaml_file


class ModelRuntimePolicyService:
    def load_policy(self) -> ModelRuntimePolicy:
        data = load_yaml_file(PATHS.config_root / "models" / "model_runtime_policy.yaml", critical=True, root=PATHS.config_root / "models")
        runtime = data.get("runtime", {}) if isinstance(data.get("runtime", {}), dict) else {}
        limits = data.get("limits", {}) if isinstance(data.get("limits", {}), dict) else {}
        return ModelRuntimePolicy(
            chat_auto_use_enabled=bool(runtime.get("chat_auto_use_enabled", False)),
            role_pipeline_auto_use_enabled=bool(runtime.get("role_pipeline_auto_use_enabled", False)),
            first_token_probe_enabled_by_default=bool(runtime.get("first_token_probe_enabled_by_default", False)),
            tool_calling_enabled=bool(runtime.get("tool_calling_enabled", False)),
            network_download_enabled=bool(runtime.get("network_download_enabled", False)),
            max_auto_parameter_class=str(limits.get("max_auto_parameter_class", "7b")),
            manual_only_parameter_classes=[str(item) for item in limits.get("manual_only_parameter_classes", []) or []],
        )

    def status(self) -> dict[str, object]:
        policy = self.load_policy()
        return {"status": "ok", "service": "model_runtime_policy", **policy.model_dump()}
