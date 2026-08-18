from pathlib import Path

from aipinho.schemas.tools.tool_call import ToolCall
from aipinho.services.tools.tool_dry_run_executor import ToolDryRunExecutor
from aipinho.services.tools.tool_preview_service import ToolPreviewService


def _run(call: ToolCall):
    plan = ToolPreviewService().plan_from_calls([call])
    return ToolDryRunExecutor().dry_run(plan)


def test_read_file_simulated():
    result = _run(ToolCall(tool_id="filesystem.read_file", input={"workspace": r"C:\Dev\AIpinho", "path": "README.md"}))
    assert result.status == "simulated"
    assert result.safe_to_execute is False
    assert "not executed" in result.summary


def test_write_file_simulated_no_write(tmp_path):
    target = tmp_path / "not_written.txt"
    result = _run(ToolCall(tool_id="filesystem.write_file", input={"path": str(target), "content_preview": "x"}))
    assert result.status == "needs_approval"
    assert target.exists() is False
    assert result.safe_to_execute is False


def test_shell_simulated_no_command(tmp_path):
    target = tmp_path / "shell_should_not_create.txt"
    result = _run(ToolCall(tool_id="shell.run_command", input={"command": f"New-Item {target}"}))
    assert result.status == "needs_approval"
    assert target.exists() is False
    assert "not executed" in result.tool_results[0].would_do


def test_git_simulated_no_git_call():
    result = _run(ToolCall(tool_id="git.status", input={"workspace": r"C:\Dev\AIpinho"}))
    assert result.status == "simulated"
    assert "git was not called" in result.tool_results[0].would_do


def test_trace_present():
    result = _run(ToolCall(tool_id="filesystem.read_file", input={"workspace": r"C:\Dev\AIpinho", "path": "."}))
    assert result.trace
    assert result.tool_results[0].trace
