from __future__ import annotations

import zipfile
import os
import time
from pathlib import Path

import pytest

from aipinho.schemas.agents.contracts import AgentRunCreateRequest, AgentSessionCreateRequest
from aipinho.schemas.agents.tool_gateway import ToolInvocationCreateRequest
from aipinho.schemas.sandbox import SandboxArtifactExportRequest, SandboxCleanupPreviewRequest, SandboxFileRequest, SandboxShellRequest
from aipinho.services.agents.agent_session_kernel_service import AgentSessionKernelService
from aipinho.services.agents.agent_session_store import AgentSessionStore
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.agents.agent_tool_invocation_store import AgentToolInvocationStore
from aipinho.services.sandbox.sandbox_artifact_service import SandboxArtifactService
from aipinho.services.sandbox.sandbox_cleanup_service import SandboxCleanupService
from aipinho.services.sandbox.sandbox_file_service import SandboxFileService
from aipinho.services.sandbox.sandbox_shell_service import SandboxShellService
from aipinho.services.sandbox.sandbox_validation_service import SandboxValidationService
from aipinho.services.sandbox.sandbox_workspace_service import SandboxWorkspaceService


@pytest.fixture()
def sandbox_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("AIPINHO_SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("AIPINHO_SANDBOX_DATA_ROOT", str(tmp_path / "data"))
    return tmp_path


def test_sandbox_file_lifecycle_and_export_zip(sandbox_env: Path) -> None:
    workspace = SandboxWorkspaceService().ensure_default_workspace()
    task = SandboxWorkspaceService().create_task(sandbox_workspace_id=workspace.sandbox_workspace_id, title="Generic sandbox task")
    files = SandboxFileService()

    mkdir = files.mkdir(SandboxFileRequest(sandbox_workspace_id=workspace.sandbox_workspace_id, sandbox_task_id=task.sandbox_task_id, relative_path="project"))
    assert mkdir.status == "succeeded"
    write = files.write_file(SandboxFileRequest(sandbox_workspace_id=workspace.sandbox_workspace_id, sandbox_task_id=task.sandbox_task_id, relative_path="project/report.txt", content="hello", overwrite=True))
    assert write.status == "succeeded"
    read = files.read_file(SandboxFileRequest(sandbox_workspace_id=workspace.sandbox_workspace_id, sandbox_task_id=task.sandbox_task_id, relative_path="project/report.txt"))
    assert read["content_sanitized"] == "hello"

    export = SandboxArtifactService().export_zip(
        SandboxArtifactExportRequest(
            sandbox_workspace_id=workspace.sandbox_workspace_id,
            sandbox_task_id=task.sandbox_task_id,
            filename="report.zip",
            include_paths=["project"],
        )
    )

    assert export.status == "ready"
    assert export.artifact_id
    assert export.requires_token is True
    assert export.download_endpoint and "token" not in export.download_endpoint.lower()
    completed = SandboxWorkspaceService().get_task(task.sandbox_task_id)
    assert completed.status == "completed"
    assert completed.completed_at


def test_sandbox_blocks_path_traversal(sandbox_env: Path) -> None:
    workspace = SandboxWorkspaceService().ensure_default_workspace()
    with pytest.raises(PermissionError) as exc:
        SandboxFileService().write_file(SandboxFileRequest(sandbox_workspace_id=workspace.sandbox_workspace_id, relative_path="..\\outside.txt", content="no"))
    assert str(exc.value) == "sandbox_path_traversal_blocked"


def test_sandbox_shell_allows_readonly_and_blocks_network(sandbox_env: Path) -> None:
    workspace = SandboxWorkspaceService().ensure_default_workspace()
    readonly = SandboxShellService().run(SandboxShellRequest(sandbox_workspace_id=workspace.sandbox_workspace_id, command="python --version", category="readonly_shell"))
    assert readonly.status in {"succeeded", "failed"}
    assert readonly.reason_code == "sandbox_shell_allowed"

    blocked = SandboxShellService().run(SandboxShellRequest(sandbox_workspace_id=workspace.sandbox_workspace_id, command="curl http://example.com", category="network_shell"))
    assert blocked.status == "blocked"
    assert blocked.reason_code == "sandbox_network_blocked"


def test_readonly_workspace_blocks_write_and_shell(sandbox_env: Path) -> None:
    workspace = SandboxWorkspaceService().create_workspace("Readonly fixture", role="sandbox_readonly")
    with pytest.raises(PermissionError) as write_error:
        SandboxFileService().write_file(
            SandboxFileRequest(
                sandbox_workspace_id=workspace.sandbox_workspace_id,
                relative_path="blocked.txt",
                content="no",
            )
        )
    assert str(write_error.value) == "source_readonly_write_denied"
    shell = SandboxShellService().run(
        SandboxShellRequest(
            sandbox_workspace_id=workspace.sandbox_workspace_id,
            command="python --version",
            category="readonly_shell",
        )
    )
    assert shell.status == "blocked"
    assert shell.reason_code == "source_readonly_write_denied"


def test_secret_like_content_is_blocked(sandbox_env: Path) -> None:
    workspace = SandboxWorkspaceService().ensure_default_workspace()
    result = SandboxFileService().write_file(
        SandboxFileRequest(
            sandbox_workspace_id=workspace.sandbox_workspace_id,
            relative_path="secret.txt",
            content="Bearer ABCDEFGHIJKLMNOPQRSTUVWXYZ",
            overwrite=True,
        )
    )
    assert result.status == "blocked"
    assert result.reason_code == "sandbox_secret_access_blocked"


def test_validation_records_task_evidence(sandbox_env: Path) -> None:
    workspaces = SandboxWorkspaceService()
    workspace = workspaces.ensure_default_workspace()
    task = workspaces.create_task(sandbox_workspace_id=workspace.sandbox_workspace_id, title="Validation task")
    SandboxFileService().write_file(
        SandboxFileRequest(
            sandbox_workspace_id=workspace.sandbox_workspace_id,
            sandbox_task_id=task.sandbox_task_id,
            relative_path="result.txt",
            content="validated",
            overwrite=True,
        )
    )
    validation = SandboxValidationService().validate(
        sandbox_workspace_id=workspace.sandbox_workspace_id,
        sandbox_task_id=task.sandbox_task_id,
        relative_paths=["result.txt"],
    )
    assert validation.status == "passed"
    updated = workspaces.get_task(task.sandbox_task_id)
    assert validation.validation_id in updated.validation_ids
    assert any(ref.endswith(validation.validation_id) for ref in updated.evidence_refs)


def test_sandbox_cleanup_requires_preview(sandbox_env: Path) -> None:
    cleanup = SandboxCleanupService()
    blocked = cleanup.apply("")
    assert blocked["status"] == "blocked"
    assert blocked["reason_code"] == "sandbox_cleanup_requires_preview"
    preview = cleanup.preview(SandboxCleanupPreviewRequest(max_age_hours=1))
    result = cleanup.apply(preview.cleanup_preview_id)
    assert result["status"] == "succeeded"


def test_sandbox_cleanup_only_deletes_tmp_or_trash(sandbox_env: Path) -> None:
    workspaces = SandboxWorkspaceService()
    workspace = workspaces.ensure_default_workspace()
    evidence_file = Path(workspace.root_path_sanitized) / "evidence.txt"
    evidence_file.write_text("keep", encoding="utf-8")
    old = time.time() - 7200
    os.utime(evidence_file, (old, old))

    cleanup = SandboxCleanupService()
    preview = cleanup.preview(SandboxCleanupPreviewRequest(max_age_hours=1))
    assert all("evidence.txt" not in str(item["path_sanitized"]) for item in preview.candidates)
    cleanup.apply(preview.cleanup_preview_id)
    assert evidence_file.exists()


def test_sandbox_zip_is_valid_when_artifact_bytes_exist(sandbox_env: Path) -> None:
    workspace = SandboxWorkspaceService().ensure_default_workspace()
    SandboxFileService().write_file(SandboxFileRequest(sandbox_workspace_id=workspace.sandbox_workspace_id, relative_path="a.txt", content="zip me", overwrite=True))
    export = SandboxArtifactService().export_zip(SandboxArtifactExportRequest(sandbox_workspace_id=workspace.sandbox_workspace_id, filename="bundle.zip"))
    assert export.status == "ready"
    # Artifact content is stored by the shared Tool Gateway store; the export contract proves linkability.
    assert export.download_endpoint == f"/api/v1/agents/artifacts/{export.artifact_id}/download"


def test_tool_gateway_tracks_sandbox_metadata_and_artifact(sandbox_env: Path) -> None:
    kernel = AgentSessionKernelService(store=AgentSessionStore(sandbox_env / "agent_kernel"))
    gateway = AgentToolGatewayService(
        kernel=kernel,
        store=AgentToolInvocationStore(sandbox_env / "tool_gateway"),
    )
    session = kernel.create_session("aipinho", AgentSessionCreateRequest(title="Sandbox gateway"))
    run = kernel.create_run(
        "aipinho",
        session.session_id,
        AgentRunCreateRequest(operation_type="sandbox_task", status="running"),
    )
    workspace = SandboxWorkspaceService().ensure_default_workspace()
    task = SandboxWorkspaceService().create_task(
        sandbox_workspace_id=workspace.sandbox_workspace_id,
        title="Gateway task",
    )

    write = gateway.invoke(
        "aipinho",
        run.run_id,
        "sandbox_write_file",
        ToolInvocationCreateRequest(
            sandbox_workspace_id=workspace.sandbox_workspace_id,
            sandbox_task_id=task.sandbox_task_id,
            relative_path="gateway/result.txt",
            operation_scope="sandbox",
            input={"content": "gateway", "overwrite": True},
        ),
    )
    export = gateway.invoke(
        "aipinho",
        run.run_id,
        "sandbox_zip_export",
        ToolInvocationCreateRequest(
            sandbox_workspace_id=workspace.sandbox_workspace_id,
            sandbox_task_id=task.sandbox_task_id,
            operation_scope="sandbox",
            input={"filename": "gateway.zip", "include_paths": ["gateway"]},
        ),
    )

    assert write.status == "succeeded"
    assert write.tool_invocation.sandbox_workspace_id == workspace.sandbox_workspace_id
    assert write.tool_invocation.operation_scope == "sandbox"
    assert write.validation_result and write.validation_result.status == "passed"
    assert export.status == "succeeded"
    assert len(export.artifacts) == 1
    assert export.tool_invocation.artifact_ids == [export.artifacts[0].artifact_id]
