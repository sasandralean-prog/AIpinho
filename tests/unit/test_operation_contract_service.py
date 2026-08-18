from __future__ import annotations

from pathlib import Path

from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.governance.operation_contract_service import OperationContractService


def _service(tmp_path: Path) -> OperationContractService:
    root = tmp_path / "workspace"
    root.mkdir()
    forbidden = tmp_path / "forbidden"
    forbidden.mkdir()
    registry = tmp_path / "workspace_registry.yaml"
    registry.write_text(
        f"""
schema_version: 1
workspaces:
  - workspace_id: ws_target
    root_path: "{root.as_posix()}"
    role: target_mutable
    enabled: true
  - workspace_id: ws_forbidden
    root_path: "{forbidden.as_posix()}"
    role: forbidden
    enabled: true
""",
        encoding="utf-8",
    )
    matrix = WorkspacePermissionMatrixService(registry_path=registry).load()
    return OperationContractService(permission_matrix=matrix)


def test_write_files_alias_maps_to_workspace_write_policy(tmp_path: Path):
    service = _service(tmp_path)
    root = tmp_path / "workspace"

    contract = service.build(
        source_channel="test",
        session_id="chat_test",
        user_text="Crie um arquivo no workspace.",
        intent_type="governed_file_write",
        operation_type="write_files",
        requested_actions=["write_files"],
        workspace_refs=[str(root)],
    )

    assert contract.resolved_workspace_id == "ws_target"
    assert contract.normalized_actions == ["create_file", "modify_file"]
    assert {item.decision for item in contract.permission_decisions} == {"ask"}
    assert contract.approval_required is True
    assert contract.execution_allowed is False


def test_read_only_negative_constraint_blocks_write(tmp_path: Path):
    service = _service(tmp_path)
    root = tmp_path / "workspace"

    contract = service.build(
        source_channel="test",
        session_id="chat_test",
        user_text="Apenas leia o projeto. Nao escreva e nao crie arquivo.",
        intent_type="readonly_analysis",
        operation_type="write_files",
        requested_actions=["write_files"],
        workspace_refs=[str(root)],
    )

    assert contract.negative_constraints["readonly"] is True
    assert "write" in contract.negative_constraints
    assert {item.decision for item in contract.permission_decisions} == {"denied"}
    assert "negative_constraint_blocks_action" in contract.warnings


def test_chat_only_negative_constraint_blocks_artifact(tmp_path: Path):
    service = _service(tmp_path)
    root = tmp_path / "workspace"

    contract = service.build(
        source_channel="test",
        session_id="chat_test",
        user_text="Responda somente no chat e nao gere relatorio.",
        intent_type="analysis",
        operation_type="artifact_request",
        requested_actions=["artifact_create"],
        workspace_refs=[str(root)],
    )

    assert contract.negative_constraints["chat_only"] is True
    assert contract.permission_decisions[0].decision == "denied"
    assert contract.permission_decisions[0].reason_code == "negative_constraint_blocks_action"


def test_denied_policy_returns_blocked_reason_code(tmp_path: Path):
    service = _service(tmp_path)
    forbidden = tmp_path / "forbidden"

    contract = service.build(
        source_channel="test",
        session_id="chat_test",
        user_text="Crie arquivo.",
        intent_type="governed_file_write",
        operation_type="write_files",
        requested_actions=["write_files"],
        workspace_refs=[str(forbidden)],
    )

    assert contract.resolved_workspace_id == "ws_forbidden"
    assert {item.decision for item in contract.permission_decisions} == {"denied"}
    assert "permission_denied" in contract.warnings
