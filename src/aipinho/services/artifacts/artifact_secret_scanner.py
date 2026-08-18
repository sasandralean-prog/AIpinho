from __future__ import annotations

import re

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class ArtifactSecretScanner:
    def __init__(self) -> None:
        self.policy = load_yaml_file(PATHS.config_root / "artifacts" / "artifact_content_policy.yaml", critical=True, root=PATHS.config_root / "artifacts")
        self.patterns = [re.compile(str(item), re.MULTILINE) for item in self.policy.get("secret_patterns", []) or []]

    def has_secret(self, content: str) -> bool:
        return any(pattern.search(content) for pattern in self.patterns)

    def redact(self, content: str) -> str:
        redacted = content
        for pattern in self.patterns:
            redacted = pattern.sub("[REDACTED]", redacted)
        return redacted

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "artifact_secret_scanner", "patterns": len(self.patterns)}
