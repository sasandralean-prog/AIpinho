from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.main import app
from aipinho.schemas.project_generation import ProjectGenerationRequest
from aipinho.schemas.templates import TemplateManifest
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.sandbox.sandbox_project_factory import SandboxProjectFactory
from aipinho.services.templates.template_registry_service import TemplateRegistryService
from aipinho.services.templates.template_validator import TemplateValidator


def _env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("AIPINHO_SANDBOX_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))


def test_template_registry_loads_required_catalog() -> None:
    registry = TemplateRegistryService()
    ids = {item.template_id for item in registry.list_templates()}
    assert {
        "android_kotlin_game",
        "android_kotlin_app",
        "python_cli",
        "python_fastapi",
        "static_web",
        "docs_pack",
    }.issubset(ids)
    health = registry.health()
    assert health.status == "ok"
    assert health.invalid_templates == 0


def test_template_manifest_validator_blocks_active_manifest_without_contract() -> None:
    raw = Path("tests/fixtures/templates/invalid_template_manifest.yaml").read_text(encoding="utf-8")
    import yaml

    manifest = TemplateManifest(**yaml.safe_load(raw))
    validation = TemplateValidator().validate_manifest(manifest)
    assert validation["valid"] is False
    assert "active_template_requires_project_manifest" in validation["errors"]
    assert "active_template_requires_readme" in validation["errors"]


def test_template_endpoints_expose_registry_without_raw() -> None:
    client = TestClient(app)
    status = client.get("/api/v1/templates/status")
    listing = client.get("/api/v1/templates")
    mobile = client.get("/api/v1/templates/mobile/view-model")
    assert status.status_code == 200
    assert listing.status_code == 200
    assert mobile.status_code == 200
    assert mobile.json()["raw_default_visible"] is False
    assert any(item["template_id"] == "python_fastapi" for item in listing.json()["templates"])


def test_project_factory_generates_fastapi_from_declarative_template(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    prompt = Path("tests/fixtures/templates/python_fastapi_prompt.txt").read_text(encoding="utf-8")
    result = SandboxProjectFactory().generate(
        ProjectGenerationRequest(user_goal=prompt, project_name="ApiDemo", project_type="python_fastapi", output_zip_name="apidemo.zip")
    )
    assert result.status in {"completed", "completed_with_warnings"}
    assert result.metadata_sanitized["template_id"] == "python_fastapi"
    assert any(path.endswith("app/main.py") for path in result.files_created)
    assert result.zip_artifact_id
    artifact, content = AgentToolGatewayService().read_artifact_bytes(result.zip_artifact_id)
    assert artifact.status == "ready"
    assert artifact.requires_token is True
    assert "token" not in artifact.download_endpoint.lower()
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        entries = set(archive.namelist())
    assert f"{result.project_root}/app/main.py" in entries
    assert f"{result.project_root}/PROJECT_MANIFEST.json" in entries


def test_project_factory_generates_docs_pack_from_declarative_template(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    prompt = Path("tests/fixtures/templates/docs_pack_prompt.txt").read_text(encoding="utf-8")
    result = SandboxProjectFactory().generate(ProjectGenerationRequest(user_goal=prompt, project_name="DocsDemo", project_type="docs_pack"))
    assert result.status in {"completed", "completed_with_warnings"}
    assert result.metadata_sanitized["template_id"] == "docs_pack"
    assert any(path.endswith("ARCHITECTURE.md") for path in result.files_created)
    assert any(path.endswith("RUNBOOK.md") for path in result.files_created)
    assert result.zip_artifact_id
