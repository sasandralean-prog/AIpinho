from aipinho.schemas.security.sandbox_decision import SandboxDecision
from aipinho.schemas.tools.execution_audit import ExecutionAuditEvent
from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.schemas.tools.tool_execution_result import ToolExecutionResult


def test_tool_execution_request_contract():
    request = ToolExecutionRequest(tool_id="filesystem.read_file", input={"workspace": r"C:\Dev\AIpinho", "path": "README.md"})
    assert request.mode == "readonly"
    assert request.include_content is True


def test_tool_execution_result_contract():
    result = ToolExecutionResult(execution_id="exec_1", tool_id="filesystem.read_file", status="executed_readonly", action="read_files", capability="read_workspace", side_effects=False, safe_to_execute=True)
    assert result.status == "executed_readonly"
    assert result.side_effects is False


def test_sandbox_decision_contract():
    decision = SandboxDecision(status="blocked", allowed=False, reason="outside_workspace", violations=["outside_workspace"])
    assert decision.allowed is False
    assert decision.violations == ["outside_workspace"]


def test_execution_audit_contract():
    event = ExecutionAuditEvent(audit_event_id="audit_1", execution_id="exec_1", tool_id="filesystem.read_file", status="blocked", timestamp="2026-06-07T00:00:00Z")
    assert event.bytes_read == 0
    assert event.side_effects is False
