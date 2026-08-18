from aipinho.schemas.tools.tool_call import ToolCall
from aipinho.services.tools.tool_safety_service import ToolSafetyService


def test_known_tool_allowed_for_dry_run():
    decision, tool, _ = ToolSafetyService().check(ToolCall(tool_id="filesystem.read_file", input={"workspace": r"C:\Dev\AIpinho", "path": "README.md"}))
    assert tool is not None
    assert decision.status == "allowed"
    assert decision.safe_to_dry_run is True
    assert decision.safe_to_execute is False


def test_unknown_tool_blocked():
    decision, tool, _ = ToolSafetyService().check(ToolCall(tool_id="filesystem.teleport", input={}))
    assert tool is None
    assert decision.blocked is True
    assert "unknown_tool" in decision.blocked_reasons


def test_web_tool_requires_approval():
    decision, tool, _ = ToolSafetyService().check(ToolCall(tool_id="web.request", input={"url": "https://example.invalid"}))
    assert tool is not None
    assert decision.status == "needs_approval"
    assert "web_request" in decision.approval_required_for


def test_execute_mode_requires_approval_for_shell():
    decision, _, _ = ToolSafetyService().check(ToolCall(tool_id="shell.run_command", input={"command": "echo hi"}, mode="execute"))
    assert decision.blocked is False
    assert decision.status == "needs_approval"
    assert "run_command" in decision.approval_required_for
    assert decision.safe_to_execute is False


def test_forbidden_root_blocked():
    decision, _, _ = ToolSafetyService().check(ToolCall(tool_id="filesystem.read_file", input={"workspace": r"C:\Windows", "path": "win.ini"}))
    assert decision.blocked is True
    assert "forbidden_root" in decision.blocked_reasons
    assert "tool_execute_blocked_by_workspace" in decision.blocked_reasons


def test_side_effect_marked_approval_required():
    decision, tool, _ = ToolSafetyService().check(ToolCall(tool_id="filesystem.write_file", input={"path": r"C:\Dev\AIpinho\x.txt", "content_preview": "x"}))
    assert tool is not None
    assert decision.status == "needs_approval"
    assert "write_files" in decision.approval_required_for
    assert decision.safe_to_execute is False
