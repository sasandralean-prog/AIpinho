from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class RoleInferencePolicyService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "roles" / "role_inference_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def role_inference(self) -> dict[str, Any]:
        value = self.config.get("role_inference", {})
        return value if isinstance(value, dict) else {}

    def blocked(self) -> dict[str, Any]:
        value = self.config.get("blocked", {})
        return value if isinstance(value, dict) else {}

    def allowed_runtime_types(self) -> set[str]:
        return {str(item) for item in self.config.get("allowed_runtime_types", []) or []}

    def status(self) -> dict[str, object]:
        policy = self.role_inference()
        allowed = self.allowed_runtime_types()
        return {
            "status": "ok",
            "service": "role_inference_policy",
            "enabled": bool(policy.get("enabled", True)),
            "mode": policy.get("mode", "controlled_real_inference_per_role"),
            "chat_auto_role_inference": bool(policy.get("allow_chat_auto_role_inference", False)),
            "tool_calling_enabled": False,
            "vision_runtime_enabled": "llama_cpp_vision" in allowed,
            "ocr_runtime_enabled": "llama_cpp_ocr" in allowed,
            "embedding_runtime_enabled": "llama_cpp_embedding" in allowed,
            "reranker_runtime_enabled": "llama_cpp_reranker" in allowed,
        }
