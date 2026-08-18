from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.services.tools.tool_execution_guard import ToolExecutionGuard


def _request(tool_id, workspace, path="README.md", **extra):
    data = {"workspace": str(workspace), "path": path}
    data.update(extra)
    return ToolExecutionRequest(tool_id=tool_id, input=data)


def test_guard_allows_readonly_read(tmp_path):
    (tmp_path / "README.md").write_text("ok", encoding="utf-8")
    decision, tool, _ = ToolExecutionGuard().check(_request("filesystem.read_file", tmp_path))
    assert tool is not None
    assert decision.allowed is True


def test_guard_blocks_side_effect_tools(tmp_path):
    decision, tool, _ = ToolExecutionGuard().check(_request("filesystem.write_file", tmp_path, "x.txt", content_preview="x"))
    assert tool is not None
    assert decision.allowed is False
    assert "side_effect_not_allowed" in decision.violations
    assert "write_execution_disabled_this_sprint" in decision.violations


def test_guard_blocks_shell_and_patch(tmp_path):
    shell, _, _ = ToolExecutionGuard().check(ToolExecutionRequest(tool_id="shell.run_command", input={"workspace": str(tmp_path), "path": ".", "command": "echo hi"}))
    patch, _, _ = ToolExecutionGuard().check(ToolExecutionRequest(tool_id="patch.apply", input={"workspace": str(tmp_path), "path": "."}))
    assert "shell_execution_disabled" in shell.violations
    assert "patch_apply_disabled" in patch.violations


def test_guard_blocks_mode_and_workspace_policy(tmp_path):
    bad_mode = ToolExecutionRequest.model_construct(tool_id="filesystem.read_file", input={"workspace": str(tmp_path), "path": "README.md"}, mode="execute")
    decision, _, _ = ToolExecutionGuard().check(bad_mode)
    protected, _, _ = ToolExecutionGuard().check(ToolExecutionRequest(tool_id="filesystem.read_file", input={"workspace": r"C:\PinhoabacaxiAI", "path": "."}))
    assert "mode_not_readonly" in decision.violations
    assert "protected_root" in protected.violations
