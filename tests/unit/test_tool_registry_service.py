from __future__ import annotations

import pytest

from aipinho.core.exceptions import ConfigValidationError
from aipinho.schemas.tools.tool_definition import ToolDefinition
from aipinho.services.tools.tool_registry_service import ToolRegistryService


def test_tool_registry_loads_initial_tools():
    registry = ToolRegistryService().load()
    tools = registry.list_tools()
    assert tools
    assert any(tool.execute_supported is True for tool in tools)
    assert all(
        (not tool.side_effect and tool.capability == "read_workspace")
        or (tool.requires_approval and tool.capability in {"shell", "network"})
        for tool in tools
        if tool.execute_supported
    )
    assert all(tool.dry_run_supported is True for tool in tools)


def test_tool_registry_validates_action_and_capability():
    registry = ToolRegistryService().load()
    for tool in registry.list_tools():
        assert registry.action_registry.action_exists(tool.action)
        assert registry.capability_registry.capability_exists(tool.capability)


def test_tool_definition_side_effect_requires_approval():
    with pytest.raises(ValueError):
        ToolDefinition(
            tool_id="bad.write",
            name="Bad Write",
            category="filesystem",
            adapter="filesystem",
            action="write_files",
            capability="write_workspace",
            side_effect=True,
            requires_approval=False,
        )


def test_tool_definition_governed_execute_supported_requires_approval():
    tool = ToolDefinition(
        tool_id="good.execute",
        name="Good Execute",
        category="shell",
        adapter="shell",
        action="run_command",
        capability="shell",
        side_effect=True,
        requires_approval=True,
        execute_supported=True,
    )
    assert tool.execute_supported is True


def test_disabled_tool_status_present():
    registry = ToolRegistryService().load()
    web = registry.get_tool("web.request")
    assert web is not None
    assert web.enabled is True
    assert web.requires_approval is True
    assert registry.status()["real_execution_enabled"] is True
    assert registry.status()["write_execution_enabled"] is False
    assert registry.status()["governed_execution_enabled"] is True


def test_tool_registry_capability_mismatch_degrades_by_exception(tmp_path):
    config = tmp_path / "tool_registry.yaml"
    config.write_text(
        """
schema_version: 1

tools:
  bad.read:
    name: Bad Read
    category: filesystem
    adapter: filesystem
    action: read_files
    capability: shell
    side_effect: false
    requires_approval: false
    enabled: true
    dry_run_supported: true
    execute_supported: false
""".strip(),
        encoding="utf-8",
    )
    with pytest.raises(ConfigValidationError):
        ToolRegistryService(config_path=config).load()


def test_governed_tool_registry_loads_direct_tools_as_disabled(tmp_path):
    from aipinho.repositories.tools.tool_registry_repository import ToolRegistryRepository
    from aipinho.services.tools.tool_contract_core import GovernedToolRegistryService
    registry = GovernedToolRegistryService()
    registry.repository = ToolRegistryRepository(root=tmp_path / "tools")
    assert len(registry.list_tools()) == 29
    assert registry.get('shell.powershell').default_enabled is False
    assert registry.status()['real_execution_enabled'] is False
