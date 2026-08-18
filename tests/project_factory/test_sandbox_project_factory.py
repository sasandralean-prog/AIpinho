from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.main import app
from aipinho.schemas.project_generation import ProjectGenerationRequest
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.sandbox.sandbox_project_factory import SandboxProjectFactory


def _env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("AIPINHO_SANDBOX_DATA_ROOT", str(tmp_path / "data"))
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))


def test_project_factory_detects_sandbox_project_generation(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    prompt = Path("tests/fixtures/project_factory/sapoandando_prompt.txt").read_text(encoding="utf-8")
    decision = SandboxProjectFactory().classify_goal(prompt)
    assert decision.status == "ok"
    assert decision.route_type == "sandbox_project_generation"
    assert decision.use_sandbox is True
    assert decision.project_type == "android_kotlin"
    assert decision.project_name == "SapoAndando"


def test_project_factory_prefers_explicit_project_name_over_technical_descriptors(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    factory = SandboxProjectFactory()
    assert factory.infer_project_name("Crie um projeto Python CLI chamado FileLister e gere zip.") == "FileLister"
    assert factory.infer_project_name("Create an Android Kotlin project named JumpGame and export a zip.") == "JumpGame"


def test_project_factory_sapoandando_generates_expected_zip(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    prompt = Path("tests/fixtures/project_factory/sapoandando_prompt.txt").read_text(encoding="utf-8")
    result = SandboxProjectFactory().generate(
        ProjectGenerationRequest(
            user_goal=prompt,
            project_name="SapoAndando",
            project_type="android_kotlin",
            requested_assets=["sapo.png", "encanamento.png"],
            output_zip_name="sapoandando.zip",
        )
    )

    assert result.status == "completed_with_warnings"
    assert result.zip_artifact_id
    assert result.download_endpoint and "token" not in result.download_endpoint.lower()
    assert result.requires_token is True
    assert any(path.endswith("GameView.kt") for path in result.files_created)
    assert any(path.endswith("sapo.xml") for path in result.assets_created)
    assert any(path.endswith("encanamento.xml") for path in result.assets_created)
    assert result.validation_ids
    assert "Artifact pronto" in result.final_answer_sanitized

    artifact, content = AgentToolGatewayService().read_artifact_bytes(result.zip_artifact_id)
    assert artifact.status == "ready"
    assert artifact.requires_token is True
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        entries = set(archive.namelist())
        assert archive.testzip() is None
    assert f"{result.project_root}/README.md" in entries
    assert f"{result.project_root}/PROJECT_MANIFEST.json" in entries
    assert any(entry.endswith("GameView.kt") for entry in entries)
    assert "sandbox_manifest.json" in entries


def test_project_factory_python_and_web_templates(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    factory = SandboxProjectFactory()
    python_result = factory.generate(ProjectGenerationRequest(user_goal="Crie uma ferramenta Python CLI e gere zip.", project_name="FileLister", project_type="python_cli"))
    web_result = factory.generate(ProjectGenerationRequest(user_goal="Crie uma landing page HTML CSS JS e gere zip.", project_name="NeonLanding", project_type="static_web"))

    assert python_result.zip_artifact_id
    assert web_result.zip_artifact_id
    assert any(path.endswith("main.py") for path in python_result.files_created)
    assert any(path.endswith("index.html") for path in web_result.files_created)


def test_project_factory_external_path_requires_workspace_and_offers_sandbox_alternative(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    prompt = r"Analise C:\Users\someone\Documents\ProjetoNaoRegistrado e empacote."
    result = SandboxProjectFactory().generate(ProjectGenerationRequest(user_goal=prompt))
    assert result.status == "blocked"
    assert "workspace registrado" in result.final_answer_sanitized
    assert "sandbox" in result.final_answer_sanitized
    assert result.zip_artifact_id is None


def test_project_factory_api_generate(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    client = TestClient(app)
    response = client.post(
        "/api/v1/sandbox/project-factory/generate",
        json={
            "user_goal": "Crie uma landing page HTML CSS JS e gere zip.",
            "project_name": "ApiWeb",
            "project_type": "static_web",
            "output_zip_name": "apiweb.zip",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["zip_artifact_id"]
    assert payload["status"] == "completed"
    assert payload["download_endpoint"]
