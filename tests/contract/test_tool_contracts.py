from __future__ import annotations

import pytest
from pydantic import ValidationError

from aipinho.schemas.tools.tool_call import ToolCall
from aipinho.schemas.tools.tool_definition import ToolDefinition
from aipinho.schemas.tools.tool_dry_run import ToolDryRunPlan, ToolDryRunResult
from aipinho.schemas.tools.tool_result import ToolDryRunResultItem


def test_tool_definition_schema():
    tool = ToolDefinition(
        tool_id="filesystem.read_file",
        name="Read File",
        category="filesystem",
        adapter="filesystem",
        action="read_files",
        capability="read_workspace",
    )
    assert tool.execute_supported is False
    assert tool.dry_run_supported is True


def test_tool_definition_invalid_category():
    with pytest.raises(ValidationError):
        ToolDefinition(tool_id="x", name="X", category="spaceship", adapter="x", action="read_files", capability="read_workspace")


def test_tool_call_schema_allows_execute_for_controlled_rejection():
    call = ToolCall(tool_id="shell.run_command", input={"command": "echo hi"}, mode="execute")
    assert call.mode == "execute"


def test_tool_dry_run_plan_schema():
    call = ToolCall(tool_id="filesystem.read_file", input={"path": "README.md"})
    plan = ToolDryRunPlan(source="direct", tool_calls=[call])
    assert plan.safe_to_execute is False
    assert plan.safe_to_dry_run is True


def test_tool_dry_run_result_schema():
    item = ToolDryRunResultItem(tool_id="filesystem.read_file", status="simulated", would_do="Would read; not executed.")
    result = ToolDryRunResult(dry_run_id="dry_1", status="simulated", tool_results=[item], summary="not executed")
    assert result.safe_to_execute is False
    assert result.tool_results[0].status == "simulated"


def test_governed_tool_contract_has_preview_only_boundary():
    from aipinho.schemas.tools.contracts_v2 import ToolContract
    tool = ToolContract(tool_id='x', provider='p', display_name='X')
    assert tool.allowed_call_modes == ['preview_only']
    assert 'direct_execution' in tool.forbidden_call_modes
