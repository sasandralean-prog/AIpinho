from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from aipinho.core.paths import PATHS


class HybridExecutionPolicyService:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or PATHS.config_root / "agents" / "hybrid_execution_policy.yaml"

    def load(self) -> dict[str, Any]:
        if not self.path.exists():
            raise FileNotFoundError("hybrid_execution_policy_missing")
        payload = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict) or not isinstance(payload.get("codex"), dict):
            raise ValueError("hybrid_execution_policy_invalid")
        return payload

    def codex(self) -> dict[str, Any]:
        return self.load()["codex"]

    def islands(self) -> dict[str, Any]:
        islands = dict(self.load().get("interpretation_islands", {}) or {})
        allowed = list(islands.get("allowed_agents") or [])
        lucio_enabled = (
            (os.getenv("LUCIO_ENABLED") or os.getenv("LUCIO_AGENT_ENABLED") or "")
            .strip()
            .lower()
            in {"1", "true", "yes", "on"}
        )
        if lucio_enabled and "lucio" not in allowed:
            allowed.append("lucio")
        islands["allowed_agents"] = allowed
        return islands

    def log_summary(self) -> dict[str, Any]:
        return self.load().get("log_summary", {})
