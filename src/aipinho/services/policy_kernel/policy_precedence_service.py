from __future__ import annotations

from pathlib import Path

from aipinho.core.exceptions import ConfigValidationError
from aipinho.core.paths import PATHS
from aipinho.schemas.policy.policy_trace import PolicyPrecedenceConfig
from aipinho.utils.yaml_loader import load_yaml_file


class PolicyPrecedenceService:
    REQUIRED_RULES = (
        "forbidden_root",
        "explicit_user_denial",
        "security_policy_denial",
        "read_only_constraint",
        "success_contract_constraint",
        "capability_gate",
        "task_contract",
        "approval_policy",
        "role_declared_policy",
        "tool_default_policy",
        "default_deny",
    )

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "policies" / "policy_precedence.yaml"
        self._config: PolicyPrecedenceConfig | None = None

    def load(self) -> "PolicyPrecedenceService":
        data = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self._config = PolicyPrecedenceConfig(**data)
        self.validate()
        return self

    @property
    def config(self) -> PolicyPrecedenceConfig:
        if self._config is None:
            self.load()
        if self._config is None:
            raise ConfigValidationError("Policy precedence could not be loaded")
        return self._config

    def validate(self) -> None:
        order = self.config.precedence
        missing = [rule for rule in self.REQUIRED_RULES if rule not in order]
        if missing:
            raise ConfigValidationError(f"Missing policy precedence rules: {missing}")
        if order.index("default_deny") != len(order) - 1:
            raise ConfigValidationError("default_deny must be the final policy rule")
        if order.index("forbidden_root") > order.index("role_declared_policy"):
            raise ConfigValidationError("forbidden_root must precede role_declared_policy")
        if order.index("approval_policy") > order.index("role_declared_policy"):
            raise ConfigValidationError("approval_policy must precede role_declared_policy")
        if order.index("role_declared_policy") < order.index("capability_gate"):
            raise ConfigValidationError("role_declared_policy cannot precede capability_gate")

    def ordered_rules(self) -> list[str]:
        self.validate()
        return list(self.config.precedence)

    def explain(self) -> dict[str, object]:
        return {"precedence": self.ordered_rules(), "rules": self.config.rules}

    def status(self) -> dict[str, object]:
        try:
            self.validate()
            return {"status": "ok", "rules": len(self.config.precedence)}
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)}

