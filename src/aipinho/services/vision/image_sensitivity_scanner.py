from __future__ import annotations

import re

from aipinho.services.vision.config import vision_config


class ImageSensitivityScanner:
    def __init__(self, config: dict | None = None) -> None:
        self.config = config or vision_config("image_sensitivity_policy.yaml")

    def scan_text(self, text: str) -> dict[str, object]:
        blocked: list[str] = []
        patterns = ((self.config.get("patterns", {}) or {}).get("secret_like", []) if isinstance(self.config.get("patterns", {}), dict) else [])
        for pattern in patterns:
            if re.search(str(pattern), text or ""):
                blocked.append("secret_detected")
                break
        return {"status": "ok" if not blocked else "blocked", "allowed": not blocked, "blocked_reasons": blocked, "warnings": []}

    def redact(self, text: str) -> str:
        return re.sub(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*[^\s]+", r"\1=<redacted>", text or "")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "image_sensitivity_scanner", "secret_scan_enabled": True}
