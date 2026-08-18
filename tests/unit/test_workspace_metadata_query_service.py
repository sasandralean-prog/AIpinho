from __future__ import annotations

from pathlib import Path

from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision
from aipinho.services.chat.workspace_metadata_query_service import WorkspaceMetadataQueryService
from aipinho.services.policy_kernel.workspace_role_contract_service import WorkspaceRoleContractService


def test_workspace_metadata_query_reads_only_and_reports_requested_files(tmp_path: Path) -> None:
    workspace = tmp_path / "project"
    workspace.mkdir()
    (workspace / "build.gradle").write_text("plugins {}\n", encoding="utf-8")
    (workspace / "package.json").write_text('{"scripts": {}}\n', encoding="utf-8")
    (workspace / "src").mkdir()
    registry = tmp_path / "workspace_registry.yaml"
    registry.write_text(
        "\n".join(
            [
                "schema_version: 1",
                "workspaces:",
                "  - workspace_id: test_project",
                f"    root_path: {workspace.as_posix()}",
                "    role: target_mutable",
                "    read_allowed: true",
                "    write_allowed: true",
            ]
        ),
        encoding="utf-8",
    )
    decision = ChatOperationDecision(
        operation_id="chatop_test",
        operation_type="workspace_metadata_query",
        message_type="assistant_final_answer",
        confidence=0.9,
        workspace=str(workspace),
        metadata={
            "requested_files": ["build.gradle", "package.json"],
            "entrypoint_patterns": ["build.gradle", "package.json", "src"],
        },
    )

    service = WorkspaceMetadataQueryService(
        workspace_service=WorkspaceRoleContractService(config_path=registry).load(),
    )
    response = service.respond(session_id="chat_test", decision=decision)

    assert response.status == "ok"
    assert response.operation_type == "workspace_metadata_query"
    assert response.policy["workspace_write"] is False
    assert response.intent["requires_task"] is False
    assert "build.gradle: sim" in response.message
    assert "package.json: sim" in response.message
    assert "Nao criei arquivo" in response.message
    assert not (workspace / "1. existe build.gradle").exists()
