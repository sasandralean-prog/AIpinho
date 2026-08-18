from __future__ import annotations

from pathlib import Path

from aipinho.schemas.sandbox import SandboxFileRequest
from aipinho.services.sandbox.sandbox_file_service import SandboxFileService
from aipinho.services.sandbox.sandbox_workspace_service import SandboxWorkspaceService


def test_sandbox_regression_contract_blocks_escape_and_allows_local_write(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("AIPINHO_SANDBOX_DATA_ROOT", str(tmp_path / "data"))
    workspace = SandboxWorkspaceService().ensure_default_workspace()
    service = SandboxFileService()

    allowed = service.write_file(SandboxFileRequest(sandbox_workspace_id=workspace.sandbox_workspace_id, relative_path="creative/output.txt", content="inside", overwrite=True))
    assert allowed.status == "succeeded"

    try:
        service.write_file(SandboxFileRequest(sandbox_workspace_id=workspace.sandbox_workspace_id, relative_path="../outside.txt", content="outside"))
    except PermissionError as exc:
        assert str(exc) == "sandbox_path_traversal_blocked"
    else:  # pragma: no cover
        raise AssertionError("sandbox escape should be blocked")
