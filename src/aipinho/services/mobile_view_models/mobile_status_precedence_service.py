from __future__ import annotations

from pathlib import Path
from typing import Iterable

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class MobileStatusPrecedenceService:
    DEFAULT_ORDER = [
        "blocked",
        "failed",
        "validation_failed",
        "degraded",
        "pending_approval",
        "pending_validation",
        "running",
        "validating",
        "completed",
        "healthy",
        "idle",
        "unknown",
    ]
    DEFAULT_CARD_STATUS = {
        "validation_failed": "failed",
        "pending_approval": "pending",
        "pending_validation": "pending",
        "validating": "running",
        "idle": "healthy",
    }

    def __init__(self, policy_path: Path | None = None) -> None:
        self.policy_path = policy_path or PATHS.config_root / "mobile" / "status_precedence_policy.yaml"
        self.policy = load_yaml_file(self.policy_path, root=PATHS.project_root)

    def resolve(self, statuses: Iterable[str | None]) -> str:
        config = self.policy.get("mobile_status_precedence", {}) if isinstance(self.policy, dict) else {}
        aliases = {str(k): str(v) for k, v in (config.get("aliases", {}) or {}).items()}
        order = [str(item) for item in config.get("order", []) or self.DEFAULT_ORDER]
        card_status = {**self.DEFAULT_CARD_STATUS, **{str(k): str(v) for k, v in (config.get("card_status", {}) or {}).items()}}
        normalized = [aliases.get(str(status), str(status)) for status in statuses if status]
        if not normalized:
            normalized = ["unknown"]
        weights = {status: index for index, status in enumerate(order)}
        selected = min(normalized, key=lambda status: weights.get(status, weights.get("unknown", len(order))))
        return card_status.get(selected, selected)

    def status(self) -> dict[str, object]:
        config = self.policy.get("mobile_status_precedence", {}) if isinstance(self.policy, dict) else {}
        return {
            "status": "ok" if config.get("enabled", True) else "disabled",
            "service": "mobile_status_precedence",
            "source": str(self.policy_path),
            "order": list(config.get("order", []) or self.DEFAULT_ORDER),
        }
