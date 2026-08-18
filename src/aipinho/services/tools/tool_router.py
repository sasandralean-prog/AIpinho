from __future__ import annotations

from aipinho.schemas.tools.tool_definition import ToolDefinition
from aipinho.services.tools.tool_registry_service import ToolRegistryService


class ToolRouter:
    def __init__(self, registry: ToolRegistryService | None = None) -> None:
        self.registry = registry or ToolRegistryService().load()

    def candidates_for_action(self, action: str) -> list[ToolDefinition]:
        return self.registry.tools_for_action(action)

    def primary_tool_for_action(self, action: str) -> ToolDefinition | None:
        candidates = self.candidates_for_action(action)
        enabled = [tool for tool in candidates if tool.enabled]
        return (enabled or candidates or [None])[0]

    def map_actions(self, actions: list[str]) -> dict[str, list[str]]:
        return {action: [tool.tool_id for tool in self.candidates_for_action(action)] for action in actions}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "router": "action_to_tool_candidates", "real_execution_enabled": False}
