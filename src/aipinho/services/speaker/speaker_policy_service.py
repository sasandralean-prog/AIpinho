from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class SpeakerPolicyService:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "ux" / "speaker_policy.yaml"
        self._config: dict[str, Any] | None = None

    def load(self) -> "SpeakerPolicyService":
        self._config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        return self

    @property
    def config(self) -> dict[str, Any]:
        if self._config is None:
            self.load()
        return self._config or {}

    def status(self) -> dict[str, object]:
        try:
            defaults = self.config.get("defaults", {})
            tone = defaults.get("tone", "unknown") if isinstance(defaults, dict) else "unknown"
            return {"status": "ok", "tone": tone}
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)}