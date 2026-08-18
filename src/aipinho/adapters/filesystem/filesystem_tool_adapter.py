from __future__ import annotations

from aipinho.schemas.tools.tool_call import ToolCall
from aipinho.schemas.tools.tool_definition import ToolDefinition
from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.schemas.tools.tool_result import ToolDryRunResultItem
from aipinho.schemas.tools.tool_safety import ToolSafetyDecision
from aipinho.services.tools.filesystem_read_service import FilesystemReadService


class FilesystemToolAdapter:
    def describe(self, tool: ToolDefinition) -> dict[str, object]:
        return {"adapter": "filesystem", "tool_id": tool.tool_id, "dry_run_supported": tool.dry_run_supported, "execute_supported": tool.execute_supported}

    def validate_input(self, tool_call: ToolCall) -> dict[str, object]:
        return {"status": "delegated", "tool_call_id": tool_call.tool_call_id}

    def dry_run(self, tool: ToolDefinition, call: ToolCall, safety: ToolSafetyDecision) -> ToolDryRunResultItem:
        path = str(call.input.get("path") or call.input.get("workspace") or "contract path unavailable")
        if tool.action == "read_files":
            would_do = f"Would read file path '{path}' for analysis; not executed and no file was read."
        elif tool.action == "list_directory":
            would_do = f"Would list directory path '{path}' for analysis; not executed."
        elif tool.action == "inspect_path":
            would_do = f"Would inspect path '{path}' metadata; not executed."
        elif tool.action == "read_config":
            would_do = f"Would inspect config path '{path}' metadata; not executed."
        elif tool.action == "write_files":
            would_do = f"Would write file path '{path}' with provided content preview; not executed and no file was written."
        elif tool.action == "patch_preview":
            would_do = "Would prepare a patch preview/diff; not executed and no files were changed."
        elif tool.action == "apply_patch":
            would_do = "Would apply an approved patch in a future runtime; not executed and no patch was applied."
        else:
            would_do = f"Would simulate filesystem action '{tool.action}'; not executed."
        return ToolDryRunResultItem(tool_id=tool.tool_id, status="needs_approval" if safety.approval_required_for else "simulated", would_do=would_do, would_use_actions=[tool.action], would_require_capabilities=[tool.capability], would_require_approval=list(safety.approval_required_for), potential_side_effects=[tool.action] if tool.side_effect else [], input_valid=True, warnings=list(safety.warnings), trace=list(safety.trace))

    def execute_readonly(self, tool: ToolDefinition, request: ToolExecutionRequest):
        service = FilesystemReadService()
        if tool.action in {"inspect_path", "read_config"}:
            return service.inspect_path(request, action=tool.action, capability=tool.capability)
        if tool.action == "list_directory":
            return service.list_directory(request, action=tool.action, capability=tool.capability)
        if tool.action == "read_files":
            return service.read_file(request, action=tool.action, capability=tool.capability)
        raise NotImplementedError("filesystem_tool_not_readonly_executable")

    def execute(self, *args, **kwargs):
        raise NotImplementedError("side_effect_filesystem_execution_disabled")
