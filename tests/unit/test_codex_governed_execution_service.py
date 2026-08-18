from __future__ import annotations

import json
from pathlib import Path

from aipinho.schemas.codex_governed_execution import (
    CodexGovernedActionRequest,
    CodexGovernedContractRequest,
)
from aipinho.schemas.tools.tool_execution_result import ToolExecutionResult
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.codex_agent.codex_governed_contract_store import (
    CodexGovernedContractStore,
)
from aipinho.services.codex_agent.codex_governed_execution_service import (
    CodexGovernedExecutionService,
)
from aipinho.services.patching.apply.patch_apply_backup_service import (
    PatchApplyBackupService,
)
from aipinho.services.patching.apply.atomic_patch_write_service import (
    AtomicPatchWriteService,
)
from aipinho.services.policy_kernel.workspace_role_contract_service import (
    WorkspaceRoleContractService,
)


class FakeGovernedToolExecution:
    def __init__(self, approvals: ApprovalService) -> None:
        self.approvals = approvals
        self.executed: list[list[str]] = []

    def preview_decision(self, request):
        return {
            "allowed": True,
            "tool_id": request.tool_id,
            "action": "run_command",
            "capability": "shell",
            "violations": [],
            "warnings": [],
            "trace": [{"stage": "fake_shell_policy", "decision": "allowed"}],
            "shell_classification": {
                "category": "test_shell",
                "policy_decision": "approval_required",
            },
        }

    def request_approval(self, request):
        from datetime import datetime, timedelta, timezone

        from aipinho.schemas.approvals.approval_policy_snapshot import (
            ApprovalPolicySnapshot,
        )
        from aipinho.schemas.approvals.approval_request import ApprovalRequest

        now = datetime.now(timezone.utc)
        approval = ApprovalRequest(
            approval_id=f"approval_{request.tool_execution_request_id}",
            preview_id=request.preview_id or request.tool_execution_request_id,
            draft_id=request.draft_id or request.tool_execution_request_id,
            session_id=request.session_id,
            status="pending",
            actions_requested=["run_command"],
            approval_scope="future_execution",
            reason="fake governed shell approval",
            risk_level="medium",
            policy_snapshot=ApprovalPolicySnapshot(
                policy_status="approval_required",
                allowed_actions=["run_command"],
                approval_required_for=["run_command"],
                granted_capabilities=["shell"],
                workspace_status="target_mutable",
                risk_level="medium",
                trace_hash="fake",
            ),
            expires_at=(now + timedelta(minutes=60)).isoformat(),
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
        )
        self.approvals.store.save(approval)
        return {"status": "approval_required", "approval": approval}

    def execute(self, request):
        approval = self.approvals.get_approval(request.approval_id)
        if approval is None or approval.status != "approved":
            return ToolExecutionResult(
                execution_id="exec_blocked",
                tool_id=request.tool_id,
                status="blocked",
                violations=["approval_not_approved"],
            )
        argv = [str(item) for item in request.input["argv"]]
        self.executed.append(argv)
        return ToolExecutionResult(
            execution_id="exec_ok",
            tool_id=request.tool_id,
            status="executed_governed",
            action="run_command",
            capability="shell",
            workspace=str(request.input["workspace"]),
            metadata={"exit_code": 0},
            side_effects=True,
            safe_to_execute=True,
        )


class FailingSecondAtomicWriter:
    def __init__(self) -> None:
        self.delegate = AtomicPatchWriteService()
        self.calls = 0

    def write(self, target: Path, content: str) -> str:
        self.calls += 1
        if self.calls == 2:
            raise OSError("simulated_second_write_failure")
        return self.delegate.write(target, content)


def _write_yaml(path: Path, payload: str) -> Path:
    path.write_text(payload, encoding="utf-8")
    return path


def _service(
    tmp_path: Path, *, role: str = "target_mutable"
) -> tuple[CodexGovernedExecutionService, ApprovalService, FakeGovernedToolExecution]:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    workspace_config = _write_yaml(
        tmp_path / "workspace_registry.yaml",
        f"""
schema_version: 1
workspaces:
  - workspace_id: test_workspace
    root_path: "{str(workspace).replace(chr(92), '/')}"
    role: {role}
    approval_required: true
""".strip(),
    )
    policy = _write_yaml(
        tmp_path / "codex_policy.yaml",
        """
schema_version: 1
codex_governed_execution:
  enabled: true
  require_approval_for_every_action: true
  require_post_validation: true
  contract_ttl_minutes: 60
  max_actions_per_contract: 10
  max_file_actions_per_contract: 8
  max_shell_actions_per_contract: 4
  max_file_content_chars: 10000
  max_total_content_chars: 20000
  max_shell_timeout_seconds: 30
  allowed_action_types: [create_file, modify_file, run_shell]
  allowed_workspace_roles: [target_mutable, system_mutable]
  blocked_filename_patterns: [.env, "*.key"]
  blocked_extensions: [.exe, .dll]
  rollback_on_file_failure: true
  stop_on_action_failure: true
""".strip(),
    )
    approvals = ApprovalService(store=ApprovalStore(tmp_path / "approvals"))
    fake_tools = FakeGovernedToolExecution(approvals)
    workspace_roles = WorkspaceRoleContractService(workspace_config).load()
    service = CodexGovernedExecutionService(
        store=CodexGovernedContractStore(tmp_path / "contracts"),
        approvals=approvals,
        tool_execution=fake_tools,
        policy_path=policy,
        workspace_roles=workspace_roles,
        backups=PatchApplyBackupService(root=tmp_path / "backups"),
    )
    service._publish = lambda *args, **kwargs: None
    return service, approvals, fake_tools


def _contract_request(
    tmp_path: Path, actions: list[CodexGovernedActionRequest]
) -> CodexGovernedContractRequest:
    return CodexGovernedContractRequest(
        session_id="codex_session_test",
        objective="Apply an exact governed change.",
        workspace_path=str(tmp_path / "workspace"),
        actions=actions,
    )


def _approve_all(service, approvals, contract_id: str):
    decision = service.request_approval(contract_id)
    assert decision.status == "approval_pending"
    for approval_id in decision.contract.approval_ids:
        approvals.approve(approval_id)
    return service.refresh_approval_state(contract_id)


def test_preview_does_not_write_and_approved_create_is_validated(tmp_path):
    service, approvals, _tools = _service(tmp_path)
    target = tmp_path / "workspace" / "created.txt"
    contract = service.create_contract(
        _contract_request(
            tmp_path,
            [
                CodexGovernedActionRequest(
                    action_type="create_file",
                    target_path="created.txt",
                    content="governed content\n",
                )
            ],
        )
    )

    assert contract.status == "preview"
    assert not target.exists()
    public = service.public_contract(contract)
    assert public["actions"][0]["content"] is None
    assert public["actions"][0]["metadata"]["content_chars"] == len(
        "governed content\n"
    )

    approved = _approve_all(service, approvals, contract.contract_id)
    assert approved.status == "approved"
    result = service.execute(contract.contract_id)

    assert result.status == "completed"
    assert result.validation_status == "passed"
    assert result.safe_to_report_success is True
    assert target.read_text(encoding="utf-8") == "governed content\n"


def test_modify_detects_target_drift_after_preview(tmp_path):
    service, approvals, _tools = _service(tmp_path)
    target = tmp_path / "workspace" / "module.py"
    target.write_text("value = 1\n", encoding="utf-8")
    contract = service.create_contract(
        _contract_request(
            tmp_path,
            [
                CodexGovernedActionRequest(
                    action_type="modify_file",
                    target_path=str(target),
                    content="value = 2\n",
                )
            ],
        )
    )
    _approve_all(service, approvals, contract.contract_id)
    target.write_text("value = 99\n", encoding="utf-8")

    result = service.execute(contract.contract_id)

    assert result.status == "blocked"
    assert any("target_changed_after_preview" in reason for reason in result.blocked_reasons)
    assert target.read_text(encoding="utf-8") == "value = 99\n"


def test_shell_uses_governed_executor_only_after_approval(tmp_path):
    service, approvals, tools = _service(tmp_path)
    contract = service.create_contract(
        _contract_request(
            tmp_path,
            [
                CodexGovernedActionRequest(
                    action_type="run_shell",
                    argv=["python", "-m", "pytest", "-q"],
                    timeout_seconds=20,
                )
            ],
        )
    )

    assert tools.executed == []
    approved = _approve_all(service, approvals, contract.contract_id)
    assert approved.status == "approved"
    result = service.execute(contract.contract_id)

    assert result.status == "completed"
    assert tools.executed == [["python", "-m", "pytest", "-q"]]


def test_source_readonly_workspace_blocks_file_contract(tmp_path):
    service, _approvals, _tools = _service(tmp_path, role="source_readonly")
    contract = service.create_contract(
        _contract_request(
            tmp_path,
            [
                CodexGovernedActionRequest(
                    action_type="create_file",
                    target_path="blocked.txt",
                    content="must not be written",
                )
            ],
        )
    )

    assert contract.status == "blocked"
    assert "workspace_role_not_allowed_for_codex_execution" in contract.blocked_reasons
    assert not (tmp_path / "workspace" / "blocked.txt").exists()


def test_file_batch_rolls_back_previous_create_when_later_action_fails(tmp_path):
    service, approvals, _tools = _service(tmp_path)
    service.atomic_writer = FailingSecondAtomicWriter()
    first = tmp_path / "workspace" / "first.txt"
    second = tmp_path / "workspace" / "second.txt"
    contract = service.create_contract(
        _contract_request(
            tmp_path,
            [
                CodexGovernedActionRequest(
                    action_type="create_file",
                    target_path="first.txt",
                    content="first",
                ),
                CodexGovernedActionRequest(
                    action_type="create_file",
                    target_path="second.txt",
                    content="second",
                ),
            ],
        )
    )
    _approve_all(service, approvals, contract.contract_id)

    result = service.execute(contract.contract_id)

    assert result.status == "failed"
    assert result.execution_summary["rolled_back"] is True
    assert not first.exists()
    assert not second.exists()


def test_secret_target_and_contract_tampering_are_blocked(tmp_path):
    service, approvals, _tools = _service(tmp_path)
    secret_contract = service.create_contract(
        _contract_request(
            tmp_path,
            [
                CodexGovernedActionRequest(
                    action_type="create_file",
                    target_path=".env",
                    content="SAFE_PLACEHOLDER=value",
                )
            ],
        )
    )
    assert secret_contract.status == "blocked"
    assert "secret_target_path_blocked" in secret_contract.blocked_reasons

    contract = service.create_contract(
        _contract_request(
            tmp_path,
            [
                CodexGovernedActionRequest(
                    action_type="create_file",
                    target_path="safe.txt",
                    content="safe",
                )
            ],
        )
    )
    _approve_all(service, approvals, contract.contract_id)
    path = service.store._path(contract.contract_id)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["actions"][0]["content"] = "tampered"
    path.write_text(json.dumps(payload), encoding="utf-8")

    try:
        service.execute(contract.contract_id)
    except ValueError as exc:
        assert "codex_action_content_hash_mismatch" in str(exc)
    else:
        raise AssertionError("tampered contract must not execute")
