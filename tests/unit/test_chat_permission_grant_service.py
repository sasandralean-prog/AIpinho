from __future__ import annotations

from pathlib import Path

import yaml

from aipinho.services.chat.chat_approval_command_service import ChatApprovalCommandService
from aipinho.services.chat.chat_permission_grant_service import ChatPermissionGrantService
from aipinho.services.chat.session_grant_service import SessionGrantService
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.governance.operation_contract_service import OperationContractService


def _matrix(tmp_path: Path, workspace: Path) -> WorkspacePermissionMatrixService:
    registry = tmp_path / "workspace_registry.yaml"
    registry.write_text(
        yaml.safe_dump(
            {
                "schema_version": 1,
                "workspaces": [
                    {
                        "workspace_id": "target",
                        "root_path": str(workspace),
                        "role": "target_mutable",
                        "permissions": {"create_file": "ask", "read_file": "allowed", "list_files": "allowed"},
                    }
                ],
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return WorkspacePermissionMatrixService(registry).load()


def _service(tmp_path: Path, workspace: Path) -> tuple[ChatPermissionGrantService, SessionGrantService]:
    matrix = _matrix(tmp_path, workspace)
    grants = SessionGrantService(store_dir=tmp_path / "grants")
    contracts = OperationContractService(permission_matrix=matrix)
    return ChatPermissionGrantService(grants=grants, matrix=matrix, operation_contracts=contracts), grants


def test_chat_session_grant_create_file_from_natural_language(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    service, _grants = _service(tmp_path, workspace)

    response = service.handle(
        session_id="chat_test",
        text=f"Dou permissao para escrever no diretorio {workspace} e criar arquivos.",
        source_channel="mobile",
    )

    assert response is not None
    assert response.status == "pending_approval"
    assert response.operation_type == "session_permission_grant"
    assert "create_file" in response.actions
    assert response.contract_preview["grant"]["workspace_id"] == "target"


def test_chat_session_grant_read_workspace_from_natural_language(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    service, _grants = _service(tmp_path, workspace)

    response = service.handle(
        session_id="chat_test",
        text=f"Pode ler este workspace {workspace} durante esta sessao.",
        source_channel="launcher",
    )

    assert response is not None
    assert response.status == "pending_approval"
    assert response.contract_preview["grant"]["scope"] == "session"
    assert "read_file" in response.actions
    assert "list_files" in response.actions


def test_chat_config_grant_creates_config_change_request_preview(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    service, _grants = _service(tmp_path, workspace)

    response = service.handle(
        session_id="chat_test",
        text=f"Tornar permanente permissao para criar arquivos em {workspace}.",
        source_channel="api",
    )

    assert response is not None
    assert response.status == "preview"
    assert response.operation_type == "config_permission_grant_preview"
    assert response.policy["requires_config_change_request"] is True


def test_chat_permission_grant_uses_semantic_resolution_guard(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    service, _grants = _service(tmp_path, workspace)

    response = service.handle(
        session_id="chat_test",
        text="Nao criar grant, nao escrever arquivos; apenas preparar planejamento read-only.",
        source_channel="api",
    )

    assert response is None


def test_approve_and_deny_grant_by_chat_work(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    service, grants = _service(tmp_path, workspace)
    response = service.handle(
        session_id="chat_test",
        text=f"Dou permissao para escrever em {workspace}.",
        source_channel="mobile",
    )
    grant_id = response.contract_preview["grant"]["grant_id"]
    commands = ChatApprovalCommandService(grants=grants)

    approved = commands.handle("chat_test", f"APROVAR GRANT {grant_id}", source_channel="mobile")

    assert approved.status == "ok"
    assert approved.policy["grant_status"] == "approved"

    second = service.handle(
        session_id="chat_test",
        text=f"Dou permissao para escrever em {workspace}.",
        source_channel="mobile",
    )
    second_grant_id = second.contract_preview["grant"]["grant_id"]
    denied = commands.handle("chat_test", f"NEGAR GRANT {second_grant_id}", source_channel="mobile")

    assert denied.status == "ok"
    assert denied.policy["grant_status"] == "denied"


def test_grant_does_not_include_delete_unless_explicit(tmp_path):
    workspace = tmp_path / "project"
    workspace.mkdir()
    service, _grants = _service(tmp_path, workspace)

    response = service.handle(
        session_id="chat_test",
        text=f"Dou permissao para escrever e apagar em {workspace}.",
        source_channel="api",
    )

    assert response is not None
    assert "create_file" in response.actions
    assert "delete_file" not in response.actions
