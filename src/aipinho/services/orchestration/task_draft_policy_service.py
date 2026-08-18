from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.utils.yaml_loader import load_yaml_file


class TaskDraftPolicyService:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "runtime" / "task_draft_policy.yaml"
        self._config: dict[str, Any] | None = None

    def load(self) -> "TaskDraftPolicyService":
        self._config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        return self

    @property
    def config(self) -> dict[str, Any]:
        if self._config is None:
            self.load()
        return self._config or {}

    @property
    def task_drafts(self) -> dict[str, Any]:
        value = self.config.get("task_drafts", {})
        return value if isinstance(value, dict) else {}

    @property
    def safety(self) -> dict[str, Any]:
        value = self.config.get("safety", {})
        return value if isinstance(value, dict) else {}

    def create_for_intents(self) -> set[str]:
        return {str(item) for item in self.task_drafts.get("create_for_intents", []) or []}

    def never_create_for_intents(self) -> set[str]:
        return {str(item) for item in self.task_drafts.get("never_create_for_intents", []) or []}

    def should_create_for_intent(self, intent_type: str) -> bool:
        if intent_type in self.never_create_for_intents():
            return False
        return intent_type in self.create_for_intents()

    def ttl_minutes(self) -> int:
        return int(self.task_drafts.get("ttl_minutes", 240))

    def safe_to_execute_default(self) -> bool:
        return bool(self.task_drafts.get("safe_to_execute_default", False))

    def require_workspace_confirmation(self) -> bool:
        return bool(self.task_drafts.get("require_workspace_confirmation", True))

    def status(self) -> dict[str, object]:
        try:
            return {
                "status": "ok",
                "store": self.task_drafts.get("store", "unknown"),
                "create_for_intents": sorted(self.create_for_intents()),
                "never_create_for_intents": sorted(self.never_create_for_intents()),
                "safe_to_execute_default": self.safe_to_execute_default(),
            }
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)}