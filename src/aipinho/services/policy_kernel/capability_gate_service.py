from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from aipinho.core.exceptions import ConfigValidationError
from aipinho.core.paths import PATHS
from aipinho.schemas.policy.capability import CapabilityDecision, CapabilityDefinition, CapabilityRegistryConfig
from aipinho.schemas.policy.policy_trace import PolicyTraceItem
from aipinho.services.policy_kernel.action_registry_service import ActionRegistryService
from aipinho.services.policy_kernel.policy_trace_service import PolicyTraceService
from aipinho.utils.yaml_loader import load_yaml_file


class CapabilityRegistryService:
    REQUIRED_CAPABILITIES = {
        "read_workspace",
        "write_workspace",
        "shell",
        "git",
        "network",
        "rag",
        "memory_read",
        "memory_write",
        "model_inference",
        "artifact_write",
        "patch_preview",
        "patch_apply",
    }

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "policies" / "capability_registry.yaml"
        self._config: CapabilityRegistryConfig | None = None

    def load(self) -> "CapabilityRegistryService":
        data = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self._config = CapabilityRegistryConfig(**data)
        self.validate()
        return self

    @property
    def config(self) -> CapabilityRegistryConfig:
        if self._config is None:
            self.load()
        if self._config is None:
            raise ConfigValidationError("Capability registry could not be loaded")
        return self._config

    def validate(self) -> None:
        missing = sorted(self.REQUIRED_CAPABILITIES - set(self.config.capabilities))
        if missing:
            raise ConfigValidationError(f"Missing capabilities: {missing}")

    def list_capabilities(self) -> dict[str, CapabilityDefinition]:
        self.validate()
        return self.config.capabilities

    def canonicalize(self, capability: str) -> str:
        value = str(capability).strip()
        if value in self.config.capabilities:
            return value
        for canonical, definition in self.config.capabilities.items():
            aliases = {str(item).strip() for item in definition.aliases}
            if value in aliases:
                return canonical
        return value

    def canonicalize_all(self, capabilities: list[str] | set[str] | tuple[str, ...]) -> list[str]:
        return sorted({self.canonicalize(capability) for capability in capabilities if str(capability).strip()})

    def capability_exists(self, capability: str) -> bool:
        return self.canonicalize(capability) in self.config.capabilities

    def decide(self, capability: str, granted_capabilities: set[str] | None = None) -> CapabilityDecision:
        canonical = self.canonicalize(capability)
        granted_set = set(self.canonicalize_all(granted_capabilities or set()))
        if canonical not in self.config.capabilities:
            return CapabilityDecision(capability=canonical, granted=False, reason="unknown_capability")
        if canonical not in granted_set:
            return CapabilityDecision(capability=canonical, granted=False, reason="default_deny")
        return CapabilityDecision(capability=canonical, granted=True, reason="explicit_grant")

    def status(self) -> dict[str, object]:
        try:
            self.validate()
            aliases = sum(len(definition.aliases) for definition in self.config.capabilities.values())
            return {"status": "ok", "capabilities": len(self.config.capabilities), "aliases": aliases}
        except Exception as exc:
            return {"status": "degraded", "error": str(exc)}


@dataclass(frozen=True)
class CapabilityGateResult:
    granted_capabilities: list[str] = field(default_factory=list)
    denied_capabilities: list[str] = field(default_factory=list)
    denied_actions: list[str] = field(default_factory=list)
    reasons: dict[str, str] = field(default_factory=dict)
    trace: list[PolicyTraceItem] = field(default_factory=list)


class CapabilityGateService:
    WRITE_LIKE_CAPABILITIES = {"write_workspace", "artifact_write", "patch_apply", "memory_write", "git"}

    def __init__(
        self,
        registry: CapabilityRegistryService | None = None,
        action_registry: ActionRegistryService | None = None,
        trace_service: PolicyTraceService | None = None,
    ) -> None:
        self.registry = registry or CapabilityRegistryService().load()
        self.action_registry = action_registry or ActionRegistryService().load()
        self.trace_service = trace_service or PolicyTraceService()

    def evaluate(
        self,
        *,
        actions: list[str],
        read_only: bool,
        no_write: bool,
        no_shell: bool,
        no_network: bool,
        workspace_blocked: bool,
    ) -> CapabilityGateResult:
        granted: set[str] = set()
        denied: set[str] = set()
        denied_actions: list[str] = []
        reasons: dict[str, str] = {}
        trace: list[PolicyTraceItem] = []

        for action in actions:
            capability = self.action_registry.capability_for(action)
            if capability is None or not self.registry.capability_exists(capability):
                denied.add(capability or "unknown")
                denied_actions.append(action)
                reasons[action] = "unknown_or_missing_capability"
                trace.append(self.trace_service.create(
                    stage="capability_gate",
                    rule="unknown_capability",
                    decision="denied",
                    reason="action_has_no_known_capability",
                    severity="error",
                    source="config/policies/capability_registry.yaml",
                    input={"action": action, "capability": capability or "unknown"},
                ))
                continue

            deny_reason: str | None = None
            if workspace_blocked:
                deny_reason = "workspace_policy_denied"
            elif (read_only or no_write) and capability in self.WRITE_LIKE_CAPABILITIES:
                deny_reason = "read_only_or_no_write_constraint"
            elif read_only and capability == "shell" and self.action_registry.is_side_effect(action):
                deny_reason = "read_only_blocks_side_effect_shell"
            elif no_shell and capability == "shell":
                deny_reason = "user_constraint_no_shell"
            elif no_network and capability == "network":
                deny_reason = "user_constraint_no_network"

            if deny_reason:
                denied.add(capability)
                denied_actions.append(action)
                reasons[action] = deny_reason
                trace.append(self.trace_service.create(
                    stage="capability_gate",
                    rule=deny_reason,
                    decision="denied",
                    reason=deny_reason,
                    severity="error" if workspace_blocked else "warning",
                    source="request.user_constraints",
                    input={"action": action, "capability": capability},
                ))
                continue

            granted.add(capability)
            trace.append(self.trace_service.create(
                stage="capability_gate",
                rule="capability_granted_for_preview",
                decision="allowed",
                reason="capability_known_and_not_blocked_by_constraints",
                source="config/policies/capability_registry.yaml",
                input={"action": action, "capability": capability},
            ))

        return CapabilityGateResult(
            granted_capabilities=sorted(granted),
            denied_capabilities=sorted(denied),
            denied_actions=denied_actions,
            reasons=reasons,
            trace=trace,
        )
