from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class SessionPolicyService:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "runtime" / "session_policy.yaml"
        self._config: dict[str, Any] | None = None

    def load(self) -> "SessionPolicyService":
        self._config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        return self

    @property
    def config(self) -> dict[str, Any]:
        if self._config is None:
            self.load()
        return self._config or {}

    @property
    def session(self) -> dict[str, Any]:
        value = self.config.get("session", {})
        return value if isinstance(value, dict) else {}

    @property
    def safety(self) -> dict[str, Any]:
        value = self.config.get("safety", {})
        return value if isinstance(value, dict) else {}

    @property
    def reconciliation(self) -> dict[str, Any]:
        value = self.config.get("reconciliation", {})
        return value if isinstance(value, dict) else {}

    def ttl_minutes(self) -> int:
        return int(self.session.get("ttl_minutes", 240))

    def max_recent_messages(self) -> int:
        return int(self.session.get("max_recent_messages", 20))

    def max_message_chars(self) -> int:
        return int(self.session.get("max_message_chars", 4000))

    def store_raw_user_message(self) -> bool:
        return bool(self.session.get("store_raw_user_message", False))

    def forbidden_root_as_active_workspace(self) -> bool:
        return bool(self.safety.get("forbidden_root_as_active_workspace", False))

    def expire_sessions_on_read(self) -> bool:
        return bool(self.reconciliation.get("expire_sessions_on_read", True))

    def clear_missing_active_task_draft(self) -> bool:
        return bool(self.reconciliation.get("clear_missing_active_task_draft", True))

    def clear_active_task_draft_when_all_runs_terminal(self) -> bool:
        return bool(self.reconciliation.get("clear_active_task_draft_when_all_runs_terminal", True))

    def active_task_draft_terminal_statuses(self) -> set[str]:
        return {
            str(status)
            for status in self.reconciliation.get(
                "active_task_draft_terminal_statuses",
                ["blocked", "approved_for_future_execution", "rejected", "cancelled", "expired", "invalidated_by_policy_change", "deleted"],
            )
        }

    def status(self) -> dict[str, object]:
        try:
            return {
                "status": "ok",
                "store": self.session.get("store", "unknown"),
                "ttl_minutes": self.ttl_minutes(),
                "max_recent_messages": self.max_recent_messages(),
                "store_raw_user_message": self.store_raw_user_message(),
            }
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)}
