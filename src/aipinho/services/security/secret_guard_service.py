from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class SecretGuardService:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "security" / "secret_policy.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)

    def filename_patterns(self) -> list[str]:
        values = self.config.get("filename_patterns", [])
        return [str(item) for item in values if isinstance(item, str)]

    def is_secret_path(self, path: str | Path) -> bool:
        name = Path(path).name.lower()
        return any(fnmatch.fnmatch(name, pattern.lower()) for pattern in self.filename_patterns())

    def redact(self, text: str) -> tuple[str, list[str]]:
        detection = self.config.get("secret_detection", {}) if isinstance(self.config.get("secret_detection", {}), dict) else {}
        if not detection.get("enabled", True) or not detection.get("redact_output", True):
            return text, []
        warnings: list[str] = []
        redacted = text
        for item in self.config.get("content_patterns", []) or []:
            if not isinstance(item, dict):
                continue
            pattern = str(item.get("pattern", ""))
            replacement = str(item.get("replacement", "[REDACTED_SECRET]"))
            if not pattern:
                continue
            redacted, count = re.subn(pattern, replacement, redacted)
            if count:
                warnings.append(f"secret_redacted:{item.get('name', 'pattern')}")
        return redacted, warnings

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "secret_guard", "patterns": len(self.filename_patterns())}
