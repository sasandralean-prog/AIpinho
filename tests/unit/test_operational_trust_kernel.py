from __future__ import annotations

import json

from aipinho.repositories.regression.repositories import RegressionCandidateRepository
from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.policy_kernel.workspace_role_contract_service import WorkspaceRoleContractService
from aipinho.services.regression.operational_trust_candidate_service import OperationalTrustCandidateService
from aipinho.services.regression.regression_core import RegressionCandidateService
from aipinho.services.tools.execution_audit_service import ExecutionAuditService
from aipinho.services.tools.governed_tool_execution_service import GovernedToolExecutionService
from aipinho.services.tools.shell_command_policy_service import ShellCommandPolicyService
from aipinho.services.tools.write_capability_envelope_service import WriteCapabilityEnvelopeService
from aipinho.services.mobile_view_models.mobile_status_precedence_service import MobileStatusPrecedenceService


class _Completed:
    returncode = 0
    stdout = "ok\n"
    stderr = ""


def _runner(argv, **kwargs):
    assert kwargs["shell"] is False
    return _Completed()


def _governed_service(tmp_path):
    approvals = ApprovalService(store=ApprovalStore(root=tmp_path / "approvals"))
    audit = ExecutionAuditService(root=tmp_path / "executions", audit_log_root=tmp_path / "audit")
    return GovernedToolExecutionService(runner=_runner, approvals=approvals, audit=audit)


def _workspace_registry(tmp_path):
    source = tmp_path / "source"
    target = tmp_path / "target"
    source.mkdir()
    target.mkdir()
    registry = tmp_path / "workspace_registry.yaml"
    registry.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "workspaces:",
                "  - workspace_id: source",
                f"    root_path: \"{str(source).replace(chr(92), chr(92) + chr(92))}\"",
                "    role: source_readonly",
                "  - workspace_id: target",
                f"    root_path: \"{str(target).replace(chr(92), chr(92) + chr(92))}\"",
                "    role: target_mutable",
                "    approval_required: true",
            ]
        ),
        encoding="utf-8",
    )
    return registry, source, target


def test_workspace_role_contract_blocks_source_write_and_allows_target_patch(tmp_path):
    registry, source, target = _workspace_registry(tmp_path)
    service = WorkspaceRoleContractService(config_path=registry).load()

    source_decision = service.resolve(str(source))
    target_decision = service.resolve(str(target))
    assert source_decision.contract is not None
    assert target_decision.contract is not None

    assert service.operation_allowed(source_decision.contract, "modify_file")[0] is False
    assert service.operation_allowed(source_decision.contract, "run_shell_write")[0] is False
    assert service.operation_allowed(source_decision.contract, "run_shell_readonly")[0] is True
    assert service.operation_allowed(target_decision.contract, "apply_patch")[0] is True
    assert service.operation_allowed(target_decision.contract, "inspect_files")[0] is True
    assert service.operation_allowed(target_decision.contract, "analyze")[0] is True


def test_workspace_role_contract_prefers_more_specific_readonly_child(tmp_path):
    parent = tmp_path / "workspace"
    child = parent / "source"
    child.mkdir(parents=True)
    registry = tmp_path / "nested_workspace_registry.yaml"
    registry.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "workspaces:",
                "  - workspace_id: mutable_parent",
                f"    root_path: \"{str(parent).replace(chr(92), chr(92) + chr(92))}\"",
                "    role: target_mutable",
                "  - workspace_id: readonly_child",
                f"    root_path: \"{str(child).replace(chr(92), chr(92) + chr(92))}\"",
                "    role: source_readonly",
            ]
        ),
        encoding="utf-8",
    )

    decision = WorkspaceRoleContractService(config_path=registry).load().resolve(str(child / "module.py"))

    assert decision.contract is not None
    assert decision.contract.workspace_id == "readonly_child"
    assert decision.contract.write_allowed is False
    assert decision.trace[0]["data"]["selection_rule"] == "longest_path_then_deny_override"


def test_workspace_role_contract_restrictive_role_wins_equal_root(tmp_path):
    root = tmp_path / "workspace"
    root.mkdir()
    escaped = str(root).replace(chr(92), chr(92) + chr(92))
    registry = tmp_path / "duplicate_workspace_registry.yaml"
    registry.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "workspaces:",
                "  - workspace_id: mutable",
                f"    root_path: \"{escaped}\"",
                "    role: target_mutable",
                "  - workspace_id: forbidden",
                f"    root_path: \"{escaped}\"",
                "    role: forbidden",
            ]
        ),
        encoding="utf-8",
    )

    decision = WorkspaceRoleContractService(config_path=registry).load().resolve(str(root))

    assert decision.status == "denied"
    assert decision.contract is not None
    assert decision.contract.workspace_id == "forbidden"


def test_write_capability_envelope_requires_preview_and_binds_workspace(tmp_path):
    registry, _source, target = _workspace_registry(tmp_path)
    roles = WorkspaceRoleContractService(config_path=registry).load()
    service = WriteCapabilityEnvelopeService(workspace_roles=roles)
    target_file = target / "result.txt"

    blocked = service.create(workspace_path=str(target), target_path=str(target_file), operation_type="modify_file")
    allowed = service.create(
        workspace_path=str(target),
        target_path=str(target_file),
        operation_type="modify_file",
        preview_id="preview_1",
        approval_id="approval_1",
    )

    assert blocked.allowed is False
    assert "preview_required_for_side_effect" in blocked.envelope.blocking_reasons
    assert allowed.allowed is True
    assert allowed.envelope.workspace_id == "target"
    assert allowed.envelope.preview_id == "preview_1"
    assert allowed.envelope.approval_id == "approval_1"


def test_shell_policy_classifies_readonly_test_and_dangerous_categories():
    service = ShellCommandPolicyService()

    readonly = service.classify(argv=["python", "-c", "print('ok')"], working_dir=r"C:\Dev\AIpinho")
    test = service.classify(argv=["pytest", "-q"], working_dir=r"C:\Dev\AIpinho")
    dangerous = service.classify(command="git push origin main", working_dir=r"C:\Dev\AIpinho")

    assert readonly.category == "readonly_shell"
    assert readonly.policy_decision == "allowed"
    assert test.category == "test_shell"
    assert test.policy_decision == "approval_required"
    assert dangerous.category == "git_write_shell"
    assert dangerous.policy_decision == "blocked"


def test_governed_shell_result_contains_policy_trace_and_metadata(tmp_path):
    service = _governed_service(tmp_path)
    request = ToolExecutionRequest(
        tool_id="shell.run_command",
        mode="governed",
        input={"workspace": r"C:\Dev\AIpinho", "argv": ["python", "-c", "print('ok')"]},
    )

    approval = service.request_approval(request)["approval"]
    service.approvals.approve(approval.approval_id)
    result = service.execute(request.model_copy(update={"approval_id": approval.approval_id}))

    assert result.status == "executed_governed"
    assert result.metadata["shell_category"] == "readonly_shell"
    assert result.metadata["command_id"].startswith("cmd_")
    assert any(item["stage"] == "shell_policy" for item in result.trace)
    assert any(item["stage"] == "shell_command_finished" for item in result.trace)


def test_mobile_status_precedence_does_not_report_healthy_over_blocks():
    service = MobileStatusPrecedenceService()

    assert service.resolve(["completed", "blocked"]) == "blocked"
    assert service.resolve(["completed", "pending_approval"]) == "pending"
    assert service.resolve(["healthy", "degraded"]) == "degraded"


def test_operational_trust_candidate_sanitizes_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "aipinho.services.regression.regression_core.RegressionEventEmitter.emit",
        lambda *args, **kwargs: "event_test",
    )
    repository = RegressionCandidateRepository(root=tmp_path / "candidates")
    service = OperationalTrustCandidateService(candidates=RegressionCandidateService(repository=repository))

    candidate = service.create_for_failure(
        category="dangerous_shell_allowed",
        source="governed_tool_execution",
        expected_behavior={"status": "blocked"},
        observed_behavior={"status": "executed", "token": "sk-test-secret"},
    )

    payload = json.dumps(candidate.model_dump(), ensure_ascii=False)
    assert candidate.category == "dangerous_shell_allowed"
    assert "sk-test-secret" not in payload
