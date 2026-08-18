from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class SessionRedactionService:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "security" / "redaction_policy.yaml"
        self._config: dict[str, Any] | None = None

    def load(self) -> "SessionRedactionService":
        self._config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        return self

    @property
    def config(self) -> dict[str, Any]:
        if self._config is None:
            self.load()
        return self._config or {}

    def sanitize_message(self, message: str, *, max_chars: int = 4000) -> str:
        text = message[:max_chars]
        redaction = self.config.get("redaction", {})
        if not isinstance(redaction, dict) or not redaction.get("enabled", True):
            return text
        replacement = str(redaction.get("replacement", "[redacted]"))
        for pattern in redaction.get("secret_patterns", []) or []:
            if not isinstance(pattern, dict):
                continue
            regex = str(pattern.get("regex", ""))
            if regex:
                text = re.sub(regex, replacement, text)
        return text

    def status(self) -> dict[str, object]:
        try:
            redaction = self.config.get("redaction", {})
            return {"status": "ok", "enabled": bool(redaction.get("enabled", True)) if isinstance(redaction, dict) else False}
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)}