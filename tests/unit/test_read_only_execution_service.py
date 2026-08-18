from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.services.tools.read_only_execution_service import ReadOnlyExecutionService


def _request(tool_id, workspace, path, **extra):
    data = {"workspace": str(workspace), "path": path}
    data.update(extra)
    return ToolExecutionRequest(tool_id=tool_id, input=data)


def test_read_only_execution_allows_file_read_and_audits(tmp_path):
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    result = ReadOnlyExecutionService().execute(_request("filesystem.read_file", tmp_path, "README.md"))
    assert result.status == "executed_readonly"
    assert result.content == "hello"
    assert result.audit_event_id
    assert result.side_effects is False


def test_read_only_execution_blocks_write_shell_patch_unknown(tmp_path):
    write = ReadOnlyExecutionService().execute(_request("filesystem.write_file", tmp_path, "x.txt", content_preview="x"))
    shell = ReadOnlyExecutionService().execute(ToolExecutionRequest(tool_id="shell.run_command", input={"workspace": str(tmp_path), "path": ".", "command": "echo hi"}))
    patch = ReadOnlyExecutionService().execute(ToolExecutionRequest(tool_id="patch.apply", input={"workspace": str(tmp_path), "path": "."}))
    unknown = ReadOnlyExecutionService().execute(ToolExecutionRequest(tool_id="filesystem.unknown", input={"workspace": str(tmp_path), "path": "."}))
    assert write.status == "blocked"
    assert shell.status == "blocked"
    assert patch.status == "blocked"
    assert unknown.status == "blocked"
    assert "side_effect_not_allowed" in write.violations


def test_read_only_execution_blocks_traversal(tmp_path):
    result = ReadOnlyExecutionService().execute(_request("filesystem.read_file", tmp_path, r"..\outside.txt"))
    assert result.status == "blocked"
    assert "path_traversal" in result.violations
