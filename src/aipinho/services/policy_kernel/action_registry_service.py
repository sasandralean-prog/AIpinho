from __future__ import annotations

from pathlib import Path

from aipinho.core.exceptions import ConfigValidationError
from aipinho.core.paths import PATHS
from aipinho.schemas.policy.action import ActionDefinition, ActionRegistryConfig
from aipinho.utils.yaml_loader import load_yaml_file


class ActionRegistryService:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "policies" / "action_registry.yaml"
        self._config: ActionRegistryConfig | None = None
        self._aliases: dict[str, str] = {}

    def load(self) -> "ActionRegistryService":
        data = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self._config = ActionRegistryConfig(**data)
        self.validate()
        return self

    @property
    def config(self) -> ActionRegistryConfig:
        if self._config is None:
            self.load()
        if self._config is None:
            raise ConfigValidationError("Action registry could not be loaded")
        return self._config

    def validate(self) -> None:
        config = self.config
        aliases: dict[str, str] = {}
        for canonical, definition in config.actions.items():
            if definition.side_effect and not definition.requires_approval and not definition.approval_exception_reason:
                raise ConfigValidationError(f"Side-effect action requires approval or explicit exception: {canonical}")
            names = [canonical, *definition.aliases]
            for name in names:
                previous = aliases.get(name)
                if previous is not None and previous != canonical:
                    raise ConfigValidationError(f"Duplicate action alias '{name}' for {previous} and {canonical}")
                aliases[name] = canonical
        self._aliases = aliases

    def normalize_action(self, action_name: str) -> str:
        self.validate()
        canonical = self._aliases.get(action_name)
        if canonical is None:
            raise ConfigValidationError(f"Unknown action: {action_name}")
        return canonical

    def get_action(self, action_name: str) -> ActionDefinition:
        canonical = self.normalize_action(action_name)
        return self.config.actions[canonical]

    def action_exists(self, action_name: str) -> bool:
        try:
            self.normalize_action(action_name)
        except ConfigValidationError:
            return False
        return True

    def is_side_effect(self, action_name: str) -> bool:
        return self.get_action(action_name).side_effect

    def requires_approval(self, action_name: str) -> bool:
        return self.get_action(action_name).requires_approval

    def capability_for(self, action_name: str) -> str | None:
        return self.get_action(action_name).capability

    def list_actions(self) -> dict[str, ActionDefinition]:
        return self.config.actions

    def aliases(self) -> dict[str, str]:
        self.validate()
        return dict(self._aliases)

    def status(self) -> dict[str, object]:
        try:
            self.validate()
            return {"status": "ok", "actions": len(self.config.actions), "aliases": len(self._aliases)}
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)}

