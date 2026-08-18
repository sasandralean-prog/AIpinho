from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.chat.chat_fallback_metadata import ChatFallbackMetadata
from aipinho.utils.yaml_loader import load_yaml_file


class ChatModelFallbackService:
    def __init__(self, config_path: Path | None = None, config: dict[str, Any] | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "chat" / "chat_model_fallback_policy.yaml"
        self.config = config or load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    @property
    def fallback(self) -> dict[str, Any]:
        value = self.config.get("fallback", {})
        return value if isinstance(value, dict) else {}

    def build(self, reason: str, *, status: str = "fallback") -> ChatFallbackMetadata:
        key = {
            "blocked": "blocked_message",
            "preview": "preview_blocked_message",
            "timeout": "timeout_message",
            "unavailable": "unavailable_message",
        }.get(status, "deterministic_message")
        message = str(self.fallback.get(key) or self.fallback.get("deterministic_message") or "Resposta segura indisponivel.")
        return ChatFallbackMetadata(
            fallback_used=True,
            fallback_type="deterministic_safe_chat",
            reason=reason,
            rejected_model_content_hidden=bool(self.fallback.get("hide_rejected_model_content", True)),
            safe_message=message,
        )

    def statuses_requiring_fallback(self) -> set[str]:
        values = self.config.get("statuses_requiring_fallback", [])
        return {str(item) for item in values} if isinstance(values, list) else set()

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "chat_model_fallback", "hide_rejected_model_content": bool(self.fallback.get("hide_rejected_model_content", True))}
