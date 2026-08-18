from __future__ import annotations

from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.tools.execution_audit_service import ExecutionAuditService
from aipinho.services.tools.governed_tool_execution_service import GovernedToolExecutionService


class _Completed:
    returncode = 0
    stdout = "ok\n"
    stderr = ""


def _runner(argv, **kwargs):
    assert kwargs["shell"] is False
    assert argv[0].lower() in {"python", "python.exe", "py", "py.exe"}
    return _Completed()


def _service(tmp_path, *, runner=_runner, opener=None):
    approvals = ApprovalService(store=ApprovalStore(root=tmp_path / "approvals"))
    audit = ExecutionAuditService(root=tmp_path / "executions", audit_log_root=tmp_path / "audit")
    kwargs = {"runner": runner, "approvals": approvals, "audit": audit}
    if opener is not None:
        kwargs["opener"] = opener
    return GovernedToolExecutionService(**kwargs)


def test_governed_shell_requires_approval_before_execution(tmp_path):
    service = _service(tmp_path)
    request = ToolExecutionRequest(
        tool_id="shell.run_command",
        mode="governed",
        input={"workspace": r"C:\Dev\AIpinho", "argv": ["python", "-c", "print('ok')"]},
    )

    result = service.execute(request)

    assert result.status == "blocked"
    assert "approval_id_required" in result.violations


def test_governed_shell_executes_allowlisted_argv_after_approval(tmp_path):
    service = _service(tmp_path)
    request = ToolExecutionRequest(
        tool_id="shell.run_command",
        mode="governed",
        input={"workspace": r"C:\Dev\AIpinho", "argv": ["python", "-c", "print('ok')"]},
    )
    approval = service.request_approval(request)["approval"]
    service.approvals.approve(approval.approval_id)

    result = service.execute(request.model_copy(update={"approval_id": approval.approval_id}))

    assert result.status == "executed_governed"
    assert result.content == "ok\n"
    assert result.side_effects is True
    assert result.audit_event_id


def test_governed_shell_blocks_free_shell_and_control_operators(tmp_path):
    service = _service(tmp_path)
    request = ToolExecutionRequest(
        tool_id="shell.run_command",
        mode="governed",
        input={"workspace": r"C:\Dev\AIpinho", "command": "powershell -Command whoami && echo bad"},
    )

    approval_response = service.request_approval(request)
    result = service.execute(request)

    assert approval_response["status"] == "blocked"
    assert result.status == "blocked"
    assert "shell_category_blocked:unknown_shell" in result.violations or "shell_metacharacter_denied" in result.violations


def test_governed_web_blocks_disallowed_scheme_after_approval(tmp_path):
    service = _service(tmp_path)
    request = ToolExecutionRequest(
        tool_id="web.request",
        mode="governed",
        input={"url": "file:///C:/Windows/win.ini"},
    )
    approval = service.request_approval(request)["approval"]
    service.approvals.approve(approval.approval_id)

    result = service.execute(request.model_copy(update={"approval_id": approval.approval_id}))

    assert result.status == "blocked"
    assert "network_scheme_denied" in result.violations
