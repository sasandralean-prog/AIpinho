from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class ChatResponsePolicyService:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "ux" / "chat_response_policy.yaml"
        self._config: dict[str, Any] | None = None

    def load(self) -> "ChatResponsePolicyService":
        self._config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        return self

    @property
    def config(self) -> dict[str, Any]:
        if self._config is None:
            self.load()
        return self._config or {}

    @property
    def defaults(self) -> dict[str, Any]:
        defaults = self.config.get("defaults", {})
        return defaults if isinstance(defaults, dict) else {}

    @property
    def responses(self) -> dict[str, Any]:
        responses = self.config.get("responses", {})
        return responses if isinstance(responses, dict) else {}

    def response_for(self, key: str) -> dict[str, Any]:
        value = self.responses.get(key, {})
        return value if isinstance(value, dict) else {}

    def max_message_chars(self) -> int:
        return int(self.defaults.get("max_message_chars", 4000))

    def include_trace_by_default(self) -> bool:
        return bool(self.defaults.get("include_trace_by_default", False))

    def raw_debug_in_chat(self) -> bool:
        return bool(self.defaults.get("raw_debug_in_chat", False))

    def status(self) -> dict[str, object]:
        try:
            return {
                "status": "ok",
                "responses": sorted(self.responses.keys()),
                "max_message_chars": self.max_message_chars(),
                "raw_debug_in_chat": self.raw_debug_in_chat(),
            }
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)}