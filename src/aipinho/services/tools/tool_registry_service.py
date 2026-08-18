from __future__ import annotations

from pathlib import Path

from aipinho.core.exceptions import ConfigValidationError
from aipinho.core.paths import PATHS
from aipinho.schemas.tools.tool_definition import ToolDefinition
from aipinho.services.policy_kernel.action_registry_service import ActionRegistryService
from aipinho.services.policy_kernel.capability_gate_service import CapabilityRegistryService
from aipinho.utils.yaml_loader import load_yaml_file


class ToolRegistryService:
    SUPPORTED_ADAPTERS = {"filesystem", "shell", "git", "android", "web"}

    def __init__(self, config_path: Path | None = None, action_registry: ActionRegistryService | None = None, capability_registry: CapabilityRegistryService | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "tools" / "tool_registry.yaml"
        self.action_registry = action_registry or ActionRegistryService().load()
        self.capability_registry = capability_registry or CapabilityRegistryService().load()
        self.readonly_policy_path = PATHS.config_root / "policies" / "read_only_execution_policy.yaml"
        self.governed_policy_path = PATHS.config_root / "policies" / "governed_tool_execution_policy.yaml"
        self._tools: dict[str, ToolDefinition] | None = None
        self._warnings: list[str] = []

    def load(self) -> "ToolRegistryService":
        data = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        readonly_policy = load_yaml_file(self.readonly_policy_path, critical=True, root=self.readonly_policy_path.parent)
        governed_policy = load_yaml_file(self.governed_policy_path, critical=False, root=self.governed_policy_path.parent)
        allowed_execute_actions = set(readonly_policy.get("read_only_execution", {}).get("allowed_actions", []) or [])
        governed_execute = governed_policy.get("governed_tool_execution", {}) if isinstance(governed_policy, dict) else {}
        governed_allowed_actions = set(governed_execute.get("allowed_actions", []) or [])
        governed_allowed_capabilities = set(governed_execute.get("allowed_capabilities", []) or [])
        raw_tools = data.get("tools", {}) if isinstance(data, dict) else {}
        if not isinstance(raw_tools, dict) or not raw_tools:
            raise ConfigValidationError("tool_registry_missing_tools")
        tools: dict[str, ToolDefinition] = {}
        warnings: list[str] = []
        for tool_id, raw in raw_tools.items():
            if not isinstance(raw, dict):
                raise ConfigValidationError(f"invalid_tool_definition: {tool_id}")
            definition = ToolDefinition(tool_id=str(tool_id), **raw)
            tools[definition.tool_id] = definition
            if definition.adapter not in self.SUPPORTED_ADAPTERS:
                warnings.append(f"unknown_adapter:{definition.tool_id}:{definition.adapter}")
            if not self.action_registry.action_exists(definition.action):
                raise ConfigValidationError(f"unknown_tool_action: {definition.tool_id}:{definition.action}")
            expected_capability = self.action_registry.capability_for(definition.action)
            if not self.capability_registry.capability_exists(definition.capability):
                raise ConfigValidationError(f"unknown_tool_capability: {definition.tool_id}:{definition.capability}")
            if expected_capability and expected_capability != definition.capability:
                raise ConfigValidationError(f"tool_capability_mismatch: {definition.tool_id}:{definition.capability}!={expected_capability}")
            if definition.side_effect and not definition.requires_approval:
                raise ConfigValidationError(f"side_effect_tool_requires_approval: {definition.tool_id}")
            if definition.execute_supported and not (
                self._is_readonly_executable(definition, allowed_execute_actions)
                or self._is_governed_executable(
                    definition,
                    allowed_actions=governed_allowed_actions,
                    allowed_capabilities=governed_allowed_capabilities,
                    enabled=bool(governed_execute.get("enabled", False)),
                )
            ):
                raise ConfigValidationError(f"tool_execute_supported_without_valid_policy: {definition.tool_id}")
            if not definition.dry_run_supported:
                raise ConfigValidationError(f"tool_dry_run_required: {definition.tool_id}")
        self._tools = tools
        self._warnings = warnings
        return self

    def _is_readonly_executable(self, definition: ToolDefinition, allowed_execute_actions: set[str]) -> bool:
        return definition.enabled and not definition.side_effect and not definition.requires_approval and definition.capability == "read_workspace" and definition.action in allowed_execute_actions and definition.adapter == "filesystem"

    def _is_governed_executable(
        self,
        definition: ToolDefinition,
        *,
        allowed_actions: set[str],
        allowed_capabilities: set[str],
        enabled: bool,
    ) -> bool:
        return (
            enabled
            and definition.enabled
            and definition.requires_approval
            and definition.action in allowed_actions
            and definition.capability in allowed_capabilities
            and definition.adapter in {"shell", "web"}
        )

    @property
    def tools(self) -> dict[str, ToolDefinition]:
        if self._tools is None:
            self.load()
        return self._tools or {}

    def list_tools(self, *, include_disabled: bool = True) -> list[ToolDefinition]:
        values = list(self.tools.values())
        if not include_disabled:
            values = [item for item in values if item.enabled]
        return sorted(values, key=lambda item: item.tool_id)

    def get_tool(self, tool_id: str) -> ToolDefinition | None:
        return self.tools.get(tool_id)

    def tools_for_action(self, action: str) -> list[ToolDefinition]:
        try:
            canonical = self.action_registry.normalize_action(action)
        except Exception:
            return []
        return [tool for tool in self.list_tools() if tool.action == canonical]

    def status(self) -> dict[str, object]:
        try:
            tools = self.list_tools()
            enabled = [tool for tool in tools if tool.enabled]
            executable_readonly = [tool for tool in tools if tool.execute_supported and not tool.requires_approval]
            executable_governed = [tool for tool in tools if tool.execute_supported and tool.requires_approval]
            adapters = {adapter: "dry_run_only" for adapter in sorted(self.SUPPORTED_ADAPTERS)}
            if executable_readonly:
                adapters["filesystem"] = "read_only_execution"
            for tool in executable_governed:
                adapters[tool.adapter] = "governed_execution"
            return {"status": "ok" if not self._warnings else "degraded", "tools": len(tools), "enabled_tools": len(enabled), "disabled_tools": len(tools) - len(enabled), "read_only_executable_tools": len(executable_readonly), "governed_executable_tools": len(executable_governed), "adapters": adapters, "real_execution_enabled": bool(executable_readonly or executable_governed), "write_execution_enabled": any(tool.capability == "write_workspace" for tool in executable_governed), "governed_execution_enabled": bool(executable_governed), "warnings": list(self._warnings)}
        except Exception as exc:
            return {"status": "degraded", "error": str(exc), "real_execution_enabled": False}
