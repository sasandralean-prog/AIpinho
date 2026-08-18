from __future__ import annotations

import base64
from pathlib import Path

import pytest

from aipinho.schemas.agents.tool_gateway import ArtifactUploadRequest
from aipinho.schemas.lucio_agent import LucioAgentRequest, LucioArtifactInput
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.lucio_agent.lucio_agent_config_service import LucioAgentConfigService
from aipinho.services.lucio_agent.lucio_agent_service import LucioAgentService
from aipinho.services.lucio_agent.lucio_openai_client import FakeLucioClient
from aipinho.services.lucio_agent.lucio_route_policy_service import LucioRoutePolicyService


def _service(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> LucioAgentService:
    monkeypatch.setenv("OPENAI_ENABLED", "true")
    monkeypatch.setenv("LUCIO_ENABLED", "true")
    monkeypatch.setenv("LUCIO_AGENT_ENABLED", "true")
    monkeypatch.setenv("LUCIO_PROVIDER", "openai")
    monkeypatch.setenv("LUCIO_ALLOW_NEW_SESSIONS", "true")
    monkeypatch.setenv("LUCIO_AGENT_DEFAULT_MODEL", "lucio-test-model")
    monkeypatch.setenv("LUCIO_AGENT_USE_MEMORY_GATEWAY", "true")
    monkeypatch.setenv("LUCIO_AGENT_USE_DELEGATION", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-never-exposed")
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_AGENT_DELEGATION_ROOT", str(tmp_path / "delegations"))
    monkeypatch.setenv("AIPINHO_AGENT_MEMORY_ROOT", str(tmp_path / "memory"))
    monkeypatch.setenv("AIPINHO_POLICY_KERNEL_ROOT", str(tmp_path / "policy"))
    monkeypatch.setenv("AIPINHO_EVENT_STORE_ROOT", str(tmp_path / "events"))
    monkeypatch.setenv("AIPINHO_EVENT_RAW_ROOT", str(tmp_path / "raw"))
    monkeypatch.setenv("AIPINHO_EVENT_AUDIT_ROOT", str(tmp_path / "audit"))
    config = LucioAgentConfigService()
    return LucioAgentService(
        config_service=config,
        route_policy=LucioRoutePolicyService(config.policy_path),
        client=FakeLucioClient(),
    )


@pytest.mark.multi_agent
@pytest.mark.multimodal
def test_lucio_multimodal_image_upload_creates_artifact_and_authorized_download_ref(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session("Multimodal")
    image_bytes = b"\x89PNG\r\n\x1a\nregression-image"

    artifact = AgentToolGatewayService(kernel=service.kernel).upload_artifact(
        "lucio",
        session.session_id,
        ArtifactUploadRequest(
            filename="ui_issue.png",
            content_type="image/png",
            content=base64.b64encode(image_bytes).decode("ascii"),
            encoding="base64",
            origin="regression_fixture",
        ),
    )

    assert artifact.artifact_id
    assert artifact.size == len(image_bytes)
    assert artifact.requires_token is True
    assert artifact.download_endpoint == f"/api/v1/agents/artifacts/{artifact.artifact_id}/download"
    assert "token" not in artifact.download_endpoint.lower()


@pytest.mark.multi_agent
@pytest.mark.multimodal
def test_lucio_visual_analysis_returns_structured_answer_with_hidden_raw(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session("Visual")

    response = service.send(
        LucioAgentRequest(
            session_id=session.session_id,
            prompt="Analise essa tela e diga o que esta ruim na UX.",
            operation_type="multimodal_review",
            artifacts=[LucioArtifactInput(artifact_id="artifact_ui", filename="ui.png", content_type="image/png")],
        )
    )

    assert response.status == "completed"
    assert response.route_decision.route_type == "answer_directly"
    assert response.multimodal_message is not None
    assert response.multimodal_message.image_artifact_ids == ["artifact_ui"]
    assert "O que estou vendo" in response.text
    assert response.raw_default_visible is False
    assert "artifact:artifact_ui" in response.evidence_refs


@pytest.mark.multi_agent
@pytest.mark.multimodal
def test_lucio_visual_ambiguous_image_requests_clarification(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session("Ambiguous")

    response = service.send(
        LucioAgentRequest(
            session_id=session.session_id,
            prompt="Veja isto.",
            operation_type="lucio_chat",
            artifacts=[LucioArtifactInput(artifact_id="artifact_blurry", filename="blurry.png", content_type="image/png")],
        )
    )

    assert response.status == "completed_with_warnings"
    assert response.route_decision.route == "request_better_image"
    assert response.route_decision.clarification_question


@pytest.mark.multi_agent
@pytest.mark.multimodal
def test_lucio_multimodal_delegation_result_has_visual_evidence_refs(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session("Delegation")

    response = service.send(
        LucioAgentRequest(
            session_id=session.session_id,
            prompt="O screenshot mostra erro tecnico; delegue ao Codex um plano de correcao.",
            operation_type="coding",
            workspace_id="workspace_test",
            requested_capabilities=["read_workspace", "code_review"],
            artifacts=[LucioArtifactInput(artifact_id="artifact_error", filename="error.png", content_type="image/png")],
        )
    )

    assert response.status == "delegation_running"
    assert response.route_decision.route_type == "delegate_to_codex"
    assert response.delegation_id
    assert "artifact:artifact_error" in response.evidence_refs
    result = service.delegation_service.result(response.delegation_id)
    assert result.evidence_refs
