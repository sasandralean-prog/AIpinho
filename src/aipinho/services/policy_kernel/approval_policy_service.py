from __future__ import annotations

from pathlib import Path

from aipinho.core.exceptions import ConfigValidationError
from aipinho.core.paths import PATHS
from aipinho.schemas.policy.approval import ApprovalPolicyConfig
from aipinho.services.policy_kernel.action_registry_service import ActionRegistryService
from aipinho.utils.yaml_loader import load_yaml_file


class ApprovalPolicyService:
    def __init__(self, config_path: Path | None = None, action_registry: ActionRegistryService | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "policies" / "approval_policy.yaml"
        self.action_registry = action_registry or ActionRegistryService().load()
        self._config: ApprovalPolicyConfig | None = None
        self._actions_requiring_approval: set[str] = set()
        self._preview_allowed: set[str] = set()
        self._never_auto_execute: set[str] = set()

    def load(self) -> "ApprovalPolicyService":
        data = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self._config = ApprovalPolicyConfig(**data)
        self.validate()
        return self

    @property
    def config(self) -> ApprovalPolicyConfig:
        if self._config is None:
            self.load()
        if self._config is None:
            raise ConfigValidationError("Approval policy could not be loaded")
        return self._config

    def validate(self) -> None:
        approval = self.config.approval
        self._actions_requiring_approval = {self.action_registry.normalize_action(item) for item in approval.actions_requiring_approval}
        self._preview_allowed = {self.action_registry.normalize_action(item) for item in approval.preview_allowed_without_approval}
        self._never_auto_execute = {self.action_registry.normalize_action(item) for item in approval.never_auto_execute}
        for action_name, action in self.action_registry.list_actions().items():
            if action.side_effect and action.requires_approval and action_name not in self._actions_requiring_approval:
                raise ConfigValidationError(f"Approval policy missing side-effect action: {action_name}")

    def requires_approval(self, action_name: str) -> bool:
        try:
            canonical = self.action_registry.normalize_action(action_name)
        except ConfigValidationError:
            return self.config.approval.unknown_action_requires_approval
        action = self.action_registry.get_action(canonical)
        return canonical in self._actions_requiring_approval or action.requires_approval

    def can_preview_without_approval(self, action_name: str) -> bool:
        try:
            canonical = self.action_registry.normalize_action(action_name)
        except ConfigValidationError:
            return False
        return canonical in self._preview_allowed

    def never_auto_execute(self, action_name: str) -> bool:
        try:
            canonical = self.action_registry.normalize_action(action_name)
        except ConfigValidationError:
            return True
        return canonical in self._never_auto_execute

    def approval_actions(self) -> list[str]:
        self.validate()
        return sorted(self._actions_requiring_approval)

    def preview_actions(self) -> list[str]:
        self.validate()
        return sorted(self._preview_allowed)

    def never_auto_execute_actions(self) -> list[str]:
        self.validate()
        return sorted(self._never_auto_execute)

    def status(self) -> dict[str, object]:
        try:
            self.validate()
            return {
                "status": "ok",
                "actions_requiring_approval": self.approval_actions(),
                "preview_allowed_without_approval": self.preview_actions(),
                "never_auto_execute": self.never_auto_execute_actions(),
            }
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)}