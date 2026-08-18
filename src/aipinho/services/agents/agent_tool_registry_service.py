from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.tool_gateway import ToolDefinition, ToolRegistryStatus
from aipinho.utils.yaml_loader import load_yaml_file


class AgentToolRegistryService:
    def __init__(self, path: Path | None = None, *, root: Path | None = None) -> None:
        self.path = path or PATHS.config_root / "agents" / "tool_gateway_registry.yaml"
        self.root = root or PATHS.config_root

    def _raw_tools(self) -> list[dict[str, Any]]:
        data = load_yaml_file(self.path, critical=True, root=self.root)
        tools = data.get("tools", [])
        if not isinstance(tools, list):
            raise ValueError("tool_gateway_registry_tools_must_be_list")
        return [item for item in tools if isinstance(item, dict)]

    def list_tools(self, *, enabled: bool | None = None) -> list[ToolDefinition]:
        tools = [ToolDefinition(**item) for item in self._raw_tools()]
        seen: set[str] = set()
        duplicates: set[str] = set()
        for tool in tools:
            if tool.tool_name in seen:
                duplicates.add(tool.tool_name)
            seen.add(tool.tool_name)
        if duplicates:
            raise ValueError(f"duplicate_tool_names:{','.join(sorted(duplicates))}")
        if enabled is not None:
            tools = [tool for tool in tools if tool.enabled is enabled]
        return tools

    def get(self, tool_name: str) -> ToolDefinition | None:
        return next((tool for tool in self.list_tools() if tool.tool_name == tool_name), None)

    def require(self, tool_name: str) -> ToolDefinition:
        tool = self.get(tool_name)
        if tool is None:
            raise KeyError(tool_name)
        return tool

    def status(self) -> ToolRegistryStatus:
        tools = self.list_tools()
        enabled = [tool for tool in tools if tool.enabled]
        disabled = [tool for tool in tools if not tool.enabled]
        return ToolRegistryStatus(
            status="ok" if tools else "degraded",
            tools_loaded=len(tools),
            enabled_tools=len(enabled),
            disabled_tools=len(disabled),
            tool_names=[tool.tool_name for tool in tools],
        )
