from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.main import app
from aipinho.schemas.external_workspace import WorkspaceImportRequest, WorkspaceRegistrationRequest
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.sandbox.sandbox_autopilot_service import SandboxAutopilotService
from aipinho.services.sandbox.sandbox_workspace_service import SandboxWorkspaceService
from aipinho.services.workspaces.external_workspace_service import ExternalWorkspaceService
from aipinho.schemas.sandbox_autopilot import SandboxAutopilotRequest


def _env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("AIPINHO_SANDBOX_DATA_ROOT", str(tmp_path / "sandbox_data"))
    monkeypatch.setenv("AIPINHO_EXTERNAL_WORKSPACE_DATA_ROOT", str(tmp_path / "external_data"))
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))


def _project(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "README.md").write_text("# Example\n", encoding="utf-8")
    (root / "src").mkdir()
    (root / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (root / ".env").write_text("API_KEY=sk-test-secret-value-123456\n", encoding="utf-8")
    (root / "__pycache__").mkdir()
    (root / "__pycache__" / "main.pyc").write_bytes(b"cache")
    return root


def test_external_path_detected_and_autopilot_pauses_for_onboarding(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    source = _project(tmp_path / "external_source")
    prompt = f'Analise o projeto em "{source}" e gere um pacote.'

    candidates = ExternalWorkspaceService().detect(prompt=prompt)
    assert candidates
    assert candidates[0].exists is True
    assert any(action["action"] == "register_source_readonly" for action in candidates[0].safe_actions)

    route = SandboxAutopilotService().route(SandboxAutopilotRequest(user_goal=prompt, dry_run=True))
    assert route.status == "blocked"
    assert route.route_type == "external_path_onboarding_required"
    assert "workspace_onboarding_assistant" in route.recommended_skills


def test_source_readonly_registration_allows_read_export_and_denies_write(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    source = _project(tmp_path / "source_readonly")
    service = ExternalWorkspaceService()
    registration = service.register(WorkspaceRegistrationRequest(path=str(source), role="source_readonly"))

    assert registration.status == "registered"
    assert "read" in registration.allowed_operations
    assert "write" in registration.blocked_operations
    assert service.validate_access(registration.workspace_id, "read")["ok"] is True
    assert service.validate_access(registration.workspace_id, "write")["ok"] is False

    exported = service.export_registered_source(registration.workspace_id, filename="source_export.zip")
    assert exported.artifact_id
    assert exported.requires_token is True
    assert exported.download_endpoint and "token" not in exported.download_endpoint.lower()


def test_workspace_import_preview_apply_manifest_and_secret_scan(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    source = _project(tmp_path / "import_source")
    service = ExternalWorkspaceService()
    plan = service.preview_import(WorkspaceImportRequest(source_path=str(source), target_name="ImportedProject"))

    assert plan.status == "preview"
    assert plan.files_included >= 2
    assert not any("__pycache__" in item["relative_path"] for item in plan.included_files)
    assert plan.secret_findings
    assert plan.project_profile_candidate is not None

    result = service.apply_import(plan.import_plan_id)
    assert result.status == "imported"
    assert result.sandbox_workspace_id
    assert result.artifact_id
    assert result.validation_status == "passed"
    manifest = Path(result.sandbox_root_path or "") / "WORKSPACE_BRIDGE_MANIFEST.json"
    assert manifest.exists()
    assert (Path(result.sandbox_root_path or "") / "README.md").exists()

    artifact, content = AgentToolGatewayService().read_artifact_bytes(result.artifact_id)
    assert artifact.requires_token is True
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        names = archive.namelist()
    assert "WORKSPACE_BRIDGE_MANIFEST.json" in names


def test_workspace_onboarding_api_and_mobile_view_model(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    source = _project(tmp_path / "api_source")
    client = TestClient(app)
    response = client.post("/api/v1/workspaces/onboarding", json={"path": str(source), "requested_action": "register", "role": "source_readonly"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["registration"]["role"] == "source_readonly"

    vm = client.get("/api/v1/workspaces/mobile/onboarding")
    assert vm.status_code == 200
    assert vm.json()["registered_count"] == 1


def test_import_to_sandbox_allows_writes_without_touching_source(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    source = _project(tmp_path / "safe_source")
    before = (source / "README.md").read_text(encoding="utf-8")
    result = ExternalWorkspaceService().apply_import(
        ExternalWorkspaceService().preview_import(WorkspaceImportRequest(source_path=str(source), target_name="WritableImport")).import_plan_id
    )

    workspace = SandboxWorkspaceService().get_workspace(result.sandbox_workspace_id or "")
    assert workspace.role == "sandbox_import"
    assert "write" in workspace.allowed_operations
    assert (source / "README.md").read_text(encoding="utf-8") == before
