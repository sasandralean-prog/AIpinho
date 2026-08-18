from aipinho.schemas.tools.tool_execution_result import ToolExecutionResult
from aipinho.services.tools.execution_audit_service import ExecutionAuditService


def test_execution_audit_records_allowed_read_without_content(tmp_path):
    service = ExecutionAuditService(root=tmp_path / "executions", audit_log_root=tmp_path / "audit")
    result = ToolExecutionResult(execution_id="exec_1", tool_id="filesystem.read_file", status="executed_readonly", action="read_files", workspace=str(tmp_path), target_path=str(tmp_path / "README.md"), content="secret content", metadata={"bytes_read": 12}, safe_to_execute=True)
    event = service.record(result)
    stored = service.get_result("exec_1")
    events = service.get_events("exec_1")
    assert event.status == "executed_readonly"
    assert stored is not None
    assert stored.content is None
    assert events[0].bytes_read == 12


def test_execution_audit_records_blocked_event(tmp_path):
    service = ExecutionAuditService(root=tmp_path / "executions", audit_log_root=tmp_path / "audit")
    result = ToolExecutionResult(execution_id="exec_2", tool_id="filesystem.read_file", status="blocked", violations=["outside_workspace"], safe_to_execute=False)
    event = service.record(result)
    assert event.status == "blocked"
    assert "outside_workspace" in event.violations
