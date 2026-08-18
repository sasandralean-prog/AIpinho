from __future__ import annotations

import io
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from aipinho.main import app
from aipinho.schemas.sandbox_autopilot import SandboxAutopilotRequest
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.sandbox.sandbox_autopilot_service import SandboxAutopilotService


def _env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_SANDBOX_ROOT", str(tmp_path / "sandboxes"))
    monkeypatch.setenv("AIPINHO_SANDBOX_DATA_ROOT", str(tmp_path / "data"))


def test_sandbox_autopilot_routes_android_project_generation(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    prompt = Path("tests/fixtures/project_factory/sapoandando_prompt.txt").read_text(encoding="utf-8")
    decision = SandboxAutopilotService().route(SandboxAutopilotRequest(user_goal=prompt, dry_run=True))

    assert decision.status == "ok"
    assert decision.route_type == "sandbox_project_generation"
    assert decision.project_type == "android_kotlin"
    assert decision.project_name == "SapoAndando"
    assert "sandbox_android_kotlin_game_generator" in decision.recommended_skills


def test_sandbox_autopilot_dry_run_does_not_create_artifact(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    result = SandboxAutopilotService().run(
        SandboxAutopilotRequest(
            user_goal="Crie uma ferramenta Python CLI chamada DryRunner e gere zip.",
            dry_run=True,
        )
    )

    assert result.status == "routed"
    assert result.project_generation is None
    assert result.artifact_ids == []
    assert "Nenhum arquivo foi criado" in result.final_answer_sanitized


def test_sandbox_autopilot_generates_project_artifact(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    result = SandboxAutopilotService().run(
        SandboxAutopilotRequest(user_goal="Crie uma landing page HTML CSS JS chamada NeonSite e gere zip.")
    )

    assert result.status == "completed"
    assert result.project_generation
    assert result.project_generation.project_name == "NeonSite"
    assert result.zip_artifact_id
    assert result.requires_token is True
    assert result.validation_status == "passed"
    assert result.metadata_sanitized["autopilot_used_project_factory"] is True

    artifact, content = AgentToolGatewayService().read_artifact_bytes(result.zip_artifact_id)
    assert artifact.status == "ready"
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        entries = archive.namelist()
    assert not any("__pycache__" in entry or entry.endswith(".pyc") for entry in entries)


def test_sandbox_autopilot_blocks_external_path_without_workspace(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    result = SandboxAutopilotService().run(
        SandboxAutopilotRequest(user_goal=r"Analise C:\Users\someone\Documents\ProjetoNaoRegistrado e empacote.")
    )

    assert result.status == "blocked"
    assert result.zip_artifact_id is None
    assert "workspace registrado" in result.final_answer_sanitized
    assert "sandbox" in result.final_answer_sanitized


def test_sandbox_autopilot_api_run(tmp_path: Path, monkeypatch) -> None:
    _env(tmp_path, monkeypatch)
    client = TestClient(app)
    response = client.post(
        "/api/v1/sandbox/autopilot/run",
        json={"user_goal": "Crie uma ferramenta Python CLI chamada ApiRunner e gere zip."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "completed"
    assert payload["zip_artifact_id"]
    assert payload["route_decision"]["recommended_skills"]
