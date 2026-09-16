from __future__ import annotations

from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.patching.patch_target_guard import PatchTargetGuard
from aipinho.services.tools.execution_audit_service import ExecutionAuditService
from aipinho.services.tools.governed_tool_execution_service import GovernedToolExecutionService


def _scope(root: str, *, role: str, permissions: list[str]) -> dict:
    return {
        "version": 1,
        "source": "prompt_intent",
        "primary_workspace": root,
        "scopes": [
            {
                "scope_id": "intent_scope_test",
                "path": root,
                "role": role,
                "kind": "project",
                "readonly": role == "source_readonly",
                "mutable": role == "target_mutable",
                "declared_permissions": permissions,
                "evidence": ["unit_prompt_scope"],
                "confidence": 1.0,
            }
        ],
        "mutable_roots": [root] if role == "target_mutable" else [],
        "readonly_roots": [root] if role == "source_readonly" else [],
        "library_roots": [],
        "external_roots": [],
        "readonly_flags": {root: role == "source_readonly"},
        "workspace_ids": ["intent_scope_test"],
    }


def test_patch_target_allows_unregistered_prompt_mutable_workspace(tmp_path) -> None:
    target = tmp_path / "src" / "Player.kt"
    target.parent.mkdir()
    target.write_text("class Player\n", encoding="utf-8")
    contract = _scope(
        str(tmp_path),
        role="target_mutable",
        permissions=["read_file", "list_files", "modify_file", "apply_patch"],
    )

    decision = PatchTargetGuard().validate(
        str(tmp_path),
        str(target),
        workspace_scope_contract=contract,
    )

    assert decision.status == "allowed"
    assert "workspace_root_not_allowed" not in decision.blocked_reasons
    assert "target_root_not_allowed" not in decision.blocked_reasons


def test_patch_target_blocks_prompt_readonly_workspace(tmp_path) -> None:
    target = tmp_path / "src" / "Player.kt"
    target.parent.mkdir()
    target.write_text("class Player\n", encoding="utf-8")
    contract = _scope(
        str(tmp_path),
        role="source_readonly",
        permissions=["read_file", "list_files", "copy_from"],
    )

    decision = PatchTargetGuard().validate(
        str(tmp_path),
        str(target),
        workspace_scope_contract=contract,
    )

    assert decision.status == "blocked"
    assert "workspace_not_mutable_by_intent_scope" in decision.blocked_reasons


def _governed_service(tmp_path):
    approvals = ApprovalService(store=ApprovalStore(root=tmp_path / "approvals"))
    audit = ExecutionAuditService(
        root=tmp_path / "executions",
        audit_log_root=tmp_path / "audit",
    )
    return GovernedToolExecutionService(
        approvals=approvals,
        audit=audit,
    )


def test_governed_build_accepts_unregistered_prompt_mutable_workspace(tmp_path) -> None:
    workspace = str(tmp_path / "app")
    contract = _scope(
        workspace,
        role="target_mutable",
        permissions=[
            "read_file",
            "list_files",
            "shell_build",
            "shell_test",
            "script_execution",
        ],
    )
    request = ToolExecutionRequest(
        tool_id="shell.run_command",
        mode="governed",
        input={
            "workspace": workspace,
            "argv": ["gradlew.bat", "build"],
            "workspace_scope_contract": contract,
        },
    )

    response = _governed_service(tmp_path).request_approval(request)

    assert response["status"] == "approval_required"
    assert response["approval"].status == "pending"


def test_governed_build_blocks_prompt_readonly_workspace(tmp_path) -> None:
    workspace = str(tmp_path / "corpus")
    contract = _scope(
        workspace,
        role="source_readonly",
        permissions=["read_file", "list_files", "copy_from"],
    )
    request = ToolExecutionRequest(
        tool_id="shell.run_command",
        mode="governed",
        input={
            "workspace": workspace,
            "argv": ["gradlew.bat", "build"],
            "workspace_scope_contract": contract,
        },
    )

    response = _governed_service(tmp_path).request_approval(request)

    assert response["status"] == "blocked"
    result = response["result"]
    assert any(
        "write_envelope" in reason
        or "permission_not_declared_by_prompt_scope" in reason
        or "workspace_role_denies_shell" in reason
        for reason in result.violations
    )
