from __future__ import annotations

from aipinho.schemas.tools.tool_call import ToolCall
from aipinho.schemas.tools.tool_definition import ToolDefinition
from aipinho.schemas.tools.tool_result import ToolDryRunResultItem
from aipinho.schemas.tools.tool_safety import ToolSafetyDecision


class ShellToolAdapter:
    def describe(self, tool: ToolDefinition) -> dict[str, object]:
        return {"adapter": "shell", "tool_id": tool.tool_id, "dry_run_only": True}

    def validate_input(self, tool_call: ToolCall) -> dict[str, object]:
        return {"status": "delegated", "tool_call_id": tool_call.tool_call_id}

    def dry_run(self, tool: ToolDefinition, call: ToolCall, safety: ToolSafetyDecision) -> ToolDryRunResultItem:
        command = str(call.input.get("command") or "<command unavailable>")
        return ToolDryRunResultItem(
            tool_id=tool.tool_id,
            status="needs_approval" if safety.approval_required_for else "simulated",
            would_do=f"Would run shell command '{command}' in a future approved runtime; not executed.",
            would_use_actions=[tool.action],
            would_require_capabilities=[tool.capability],
            would_require_approval=list(safety.approval_required_for),
            potential_side_effects=[tool.action] if tool.side_effect else [],
            input_valid=True,
            warnings=list(safety.warnings),
            trace=list(safety.trace),
        )

    def execute(self, *args, **kwargs):
        raise NotImplementedError("real_shell_execution_disabled_in_sprint06")
