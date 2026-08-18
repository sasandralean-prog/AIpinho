from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class ApprovalPolicy:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "policies" / "approval_lifecycle_policy.yaml"
        self._config: dict[str, Any] | None = None

    def load(self) -> "ApprovalPolicy":
        self._config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        return self

    @property
    def config(self) -> dict[str, Any]:
        if self._config is None:
            self.load()
        return self._config or {}

    @property
    def lifecycle(self) -> dict[str, Any]:
        value = self.config.get("approval_lifecycle", {})
        return value if isinstance(value, dict) else {}

    def ttl_minutes(self) -> int:
        return int(self.lifecycle.get("default_ttl_minutes", 120))

    def approvable_actions(self) -> set[str]:
        return {str(item) for item in self.config.get("approvable_actions", []) or []}

    def blocked_actions_this_sprint(self) -> set[str]:
        return {str(item) for item in self.config.get("blocked_actions_this_sprint", []) or []}

    def safe_batch_excluded_actions(self) -> set[str]:
        batch = self.config.get("safe_batch", {})
        if not isinstance(batch, dict):
            return set()
        return {str(item) for item in batch.get("excluded_actions", []) or []}

    def never_execute_on_approval(self) -> bool:
        return bool(self.lifecycle.get("never_execute_on_approval", True))

    def require_policy_snapshot(self) -> bool:
        return bool(self.lifecycle.get("require_policy_snapshot", True))

    def can_request_actions(self, actions: list[str], approval_required_for: list[str], denied_actions: list[str]) -> tuple[bool, str]:
        if not actions:
            return False, "no_actions_requested"
        for action in actions:
            if action not in self.approvable_actions():
                return False, "unknown_action"
            if action in denied_actions and action not in approval_required_for:
                return False, "policy_denied_action"
            if action not in approval_required_for:
                return False, "action_not_marked_as_approval_required"
        return True, "ok"

    def status(self) -> dict[str, object]:
        try:
            return {
                "status": "ok",
                "approvable_actions": sorted(self.approvable_actions()),
                "blocked_actions_this_sprint": sorted(self.blocked_actions_this_sprint()),
                "safe_batch_excluded_actions": sorted(self.safe_batch_excluded_actions()),
                "never_execute_on_approval": self.never_execute_on_approval(),
            }
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)}
