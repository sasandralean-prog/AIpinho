from __future__ import annotations

import base64
from pathlib import Path

from aipinho.schemas.lucio_agent import LucioAgentRequest, LucioArtifactInput
from aipinho.schemas.agents.tool_gateway import ArtifactUploadRequest
from aipinho.services.agents.agent_tool_gateway_service import AgentToolGatewayService
from aipinho.services.lucio_agent.lucio_agent_config_service import LucioAgentConfigService
from aipinho.services.lucio_agent.lucio_agent_service import LucioAgentService
from aipinho.services.lucio_agent.lucio_openai_client import (
    FakeLucioClient,
    LucioClientResult,
    _safe_error_code,
)
from aipinho.services.lucio_agent.lucio_route_policy_service import LucioRoutePolicyService


def _service(tmp_path: Path, monkeypatch) -> LucioAgentService:
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
    monkeypatch.setenv("AIPINHO_AGENT_TOOL_GATEWAY_ROOT", str(tmp_path / "tool_gateway"))
    config = LucioAgentConfigService()
    return LucioAgentService(
        config_service=config,
        route_policy=LucioRoutePolicyService(config.policy_path),
        client=FakeLucioClient(),
    )


def test_direct_strategic_response_uses_fake_provider_and_persists_history(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session("Estrategia")

    response = service.send(
        LucioAgentRequest(
            session_id=session.session_id,
            prompt="Compare duas abordagens de arquitetura e explique os trade-offs.",
            operation_type="strategic_analysis",
        )
    )

    assert response.status == "completed"
    assert response.route_decision.route == "direct_response"
    assert response.model == "lucio-test-model"
    assert response.raw_default_visible is False
    assert [message.role for message in service.messages(session.session_id)] == ["user", "assistant"]
    assert "test-key-never-exposed" not in str(service.health())


def test_lucio_simple_greeting_routes_to_direct_response(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session("Greeting route")

    response = service.send(
        LucioAgentRequest(
            session_id=session.session_id,
            prompt="Salve lucio tudo bem?",
            operation_type="lucio_chat",
        )
    )

    assert response.status == "completed"
    assert response.route_decision.route == "direct_response"
    assert response.route_decision.route_type == "answer_directly"
    assert response.route_decision.requires_local_execution is False
    assert response.delegation_id is None


def test_lucio_default_disabled_reports_disabled_without_openai_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_ENABLED", "false")
    monkeypatch.setenv("LUCIO_ENABLED", "false")
    monkeypatch.setenv("LUCIO_AGENT_ENABLED", "false")
    monkeypatch.setenv("LUCIO_PROVIDER", "disabled")
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    service = LucioAgentService()

    health = service.health()

    assert health["status"] == "disabled_by_config"
    assert health["provider"] == "disabled"
    assert health["config"]["provider_status"] == "disabled_by_config"
    assert health["config"]["provider_required"] is False
    assert health["config"]["api_key_configured"] is False


def test_lucio_disabled_send_returns_agent_disabled_without_provider_call(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_ENABLED", "false")
    monkeypatch.setenv("LUCIO_ENABLED", "false")
    monkeypatch.setenv("LUCIO_AGENT_ENABLED", "false")
    monkeypatch.setenv("LUCIO_PROVIDER", "disabled")
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    service = LucioAgentService()

    response = service.send(
        LucioAgentRequest(
            session_id="legacy_session_readonly",
            prompt="Salve lucio tudo bem?",
            operation_type="lucio_chat",
        )
    )

    assert response.status == "blocked"
    assert response.error_code == "agent_disabled"
    assert response.provider == "disabled"
    assert response.route_decision.route == "blocked"
    assert response.route_decision.requires_local_execution is False


def test_coding_request_delegates_to_codex_with_parent_child_trace(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session()

    response = service.send(
        LucioAgentRequest(
            session_id=session.session_id,
            prompt="Implemente a correcao e rode os testes.",
            operation_type="coding",
            workspace_id="workspace_test",
            requested_capabilities=["read_workspace", "workspace_write", "validation"],
        )
    )

    assert response.status == "delegation_running"
    assert response.route_decision.route == "delegate_codex"
    assert response.delegation_id
    assert response.child_run_id
    parent = service.kernel.get_run(response.run_id)
    child = service.kernel.get_run(response.child_run_id)
    assert parent is not None and parent.agent_id == "lucio"
    assert child is not None and child.agent_id == "codex"
    assert child.parent_run_id == parent.run_id


def test_workspace_read_request_delegates_to_aipinho(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session()

    response = service.send(
        LucioAgentRequest(
            session_id=session.session_id,
            prompt="Analise o diretorio autorizado sem alterar arquivos.",
            operation_type="readonly_analysis",
            workspace_id="workspace_test",
            requested_capabilities=["read_workspace"],
        )
    )

    assert response.status == "delegation_running"
    assert response.route_decision.route == "delegate_aipinho"
    child = service.kernel.get_run(response.child_run_id)
    assert child is not None and child.agent_id == "aipinho"


def test_artifact_metadata_is_evidence_not_automatic_local_execution(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session()

    response = service.send(
        LucioAgentRequest(
            session_id=session.session_id,
            prompt="Revise este documento e apresente riscos de produto.",
            operation_type="multimodal_review",
            artifacts=[
                LucioArtifactInput(
                    artifact_id="artifact_test",
                    filename="brief.pdf",
                    content_type="application/pdf",
                )
            ],
        )
    )

    assert response.status == "completed"
    assert response.route_decision.route == "direct_response"
    assert response.route_decision.evidence_source_count == 1
    assert response.artifact_ids == ["artifact_test"]
    assert "artifact:artifact_test" in response.evidence_refs


def test_lucio_multimodal_image_upload_creates_artifact_and_structured_answer(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session()
    image_bytes = b"\x89PNG\r\n\x1a\nfake-image"
    artifact = AgentToolGatewayService(kernel=service.kernel).upload_artifact(
        "lucio",
        session.session_id,
        ArtifactUploadRequest(
            filename="mobile_ui_buttons_squeezed.png",
            content_type="image/png",
            content=base64.b64encode(image_bytes).decode("ascii"),
            encoding="base64",
            origin="test_fixture_upload",
        ),
    )

    response = service.send(
        LucioAgentRequest(
            session_id=session.session_id,
            prompt="Analise essa tela e diga o que esta ruim na UX.",
            operation_type="multimodal_review",
            artifacts=[
                LucioArtifactInput(
                    artifact_id=artifact.artifact_id,
                    filename=artifact.filename,
                    content_type=artifact.content_type,
                    preview_available=True,
                )
            ],
        )
    )

    assert response.status == "completed"
    assert response.multimodal_message is not None
    assert response.multimodal_message.image_artifact_ids == [artifact.artifact_id]
    assert response.visual_artifacts[0].requires_token is True
    assert response.route_decision.route_type == "answer_directly"
    assert "O que estou vendo" in response.text
    assert f"artifact:{artifact.artifact_id}" in response.evidence_refs
    assert response.raw_default_visible is False
    events = {event.event_type for event in service.kernel.list_run_events(response.run_id, include_hidden=True)}
    assert {"lucio_multimodal_message_created", "lucio_visual_analysis_available"} <= events


def test_lucio_ambiguous_visual_input_requests_clarification(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session()

    response = service.send(
        LucioAgentRequest(
            session_id=session.session_id,
            prompt="Veja isto.",
            operation_type="lucio_chat",
            artifacts=[
                LucioArtifactInput(
                    artifact_id="artifact_blurry",
                    filename="ambiguous_blurry_image.png",
                    content_type="image/png",
                )
            ],
        )
    )

    assert response.status == "completed_with_warnings"
    assert response.route_decision.route == "request_better_image"
    assert response.route_decision.clarification_question
    assert response.multimodal_message is not None
    assert response.raw_default_visible is False


def test_lucio_multimodal_delegation_preserves_visual_context_and_evidence(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session()

    response = service.send(
        LucioAgentRequest(
            session_id=session.session_id,
            prompt="O screenshot mostra um botao espremido; delegue ao Codex um plano de correcao.",
            operation_type="coding",
            workspace_id="workspace_test",
            requested_capabilities=["read_workspace", "code_review"],
            artifacts=[
                LucioArtifactInput(
                    artifact_id="artifact_ui",
                    filename="screen.png",
                    content_type="image/png",
                )
            ],
        )
    )

    assert response.status == "delegation_running"
    assert response.route_decision.route_type == "delegate_to_codex"
    assert response.delegation_id
    assert "artifact:artifact_ui" in response.evidence_refs
    delegation = service.delegation_service.get_delegation(response.delegation_id).delegation
    assert delegation.constraints["artifact_refs"] == ["artifact:artifact_ui"]
    assert delegation.constraints["screenshot_refs"] == ["artifact_ui"]
    assert delegation.constraints["visual_context_summary"]


def test_missing_key_status_is_degraded_without_secret_fields(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_BASE", raising=False)
    monkeypatch.delenv("OPENAI_PROJECT", raising=False)
    monkeypatch.delenv("OPENAI_PROJECT_ID", raising=False)
    monkeypatch.delenv("OPENAI_ORGANIZATION", raising=False)
    monkeypatch.delenv("OPENAI_ORG_ID", raising=False)
    monkeypatch.setenv("OPENAI_ENABLED", "true")
    monkeypatch.setenv("LUCIO_ENABLED", "true")
    monkeypatch.setenv("LUCIO_AGENT_ENABLED", "true")
    monkeypatch.setenv("LUCIO_PROVIDER", "openai")
    monkeypatch.setenv("LUCIO_ALLOW_NEW_SESSIONS", "true")
    config = LucioAgentConfigService(
        policy_path=tmp_path / "missing.yaml",
        load_environment=False,
    )
    status = config.status().model_dump()

    assert status["enabled"] is True
    assert status["api_key_configured"] is False
    assert status["provider_configured"] is False
    assert status["auth_present"] is False
    assert status["base_url_configured"] is False
    assert status["project_configured"] is False
    assert status["organization_configured"] is False
    assert status["model_configured"] is True
    assert status["model_available_or_unknown"] == "unknown"
    assert "api_key" not in status


def test_lucio_status_reports_provider_routing_without_secret_values(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_ENABLED", "true")
    monkeypatch.setenv("LUCIO_ENABLED", "true")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-never-exposed")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("OPENAI_PROJECT", "proj_test")
    monkeypatch.setenv("OPENAI_ORGANIZATION", "org_test")
    monkeypatch.setenv("LUCIO_AGENT_ENABLED", "true")
    monkeypatch.setenv("LUCIO_PROVIDER", "openai")
    monkeypatch.setenv("LUCIO_ALLOW_NEW_SESSIONS", "true")
    config = LucioAgentConfigService(
        policy_path=tmp_path / "provider.yaml",
        load_environment=False,
    )

    status = config.status().model_dump()

    assert status["api_key_configured"] is True
    assert status["provider_configured"] is True
    assert status["auth_present"] is True
    assert status["base_url_configured"] is True
    assert status["project_configured"] is True
    assert status["organization_configured"] is True
    assert status["model_configured"] is True
    assert status["model_available_or_unknown"] == "unknown"
    assert "test-key-never-exposed" not in str(status)
    assert "proj_test" not in str(status)
    assert "org_test" not in str(status)


def test_sessions_can_be_renamed_and_deleted(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    session = service.create_session("Original")
    renamed = service.rename_session(session.session_id, "Novo titulo")

    assert renamed is not None and renamed.title == "Novo titulo"
    deleted = service.delete_session(session.session_id)
    assert deleted is not None and deleted.deleted is True
    assert service.get_session(session.session_id) is None


class _InternalErrorLucioClient:
    def respond(self, **kwargs) -> LucioClientResult:
        return LucioClientResult(
            status="failed",
            text="",
            model=str(kwargs["model"]),
            error_code="openai_internal_error",
        )


class _AuthErrorLucioClient:
    def respond(self, **kwargs) -> LucioClientResult:
        return LucioClientResult(
            status="failed",
            text="",
            model=str(kwargs["model"]),
            error_code="openai_auth_error",
        )


def test_provider_internal_error_is_humanized_and_preserves_run(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    service.client = _InternalErrorLucioClient()
    session = service.create_session("Provider failure")

    response = service.send(
        LucioAgentRequest(
            session_id=session.session_id,
            prompt="Explique uma decisao de arquitetura.",
            operation_type="strategic_analysis",
        )
    )

    assert response.status == "completed_with_warnings"
    assert response.error_code == "openai_internal_error"
    assert "Nao vou inventar" in response.text
    assert "Nenhuma acao local foi executada" in response.text
    run = service.kernel.get_run(response.run_id)
    assert run is not None and run.status == "completed_with_warnings"
    assert run.error_code == "openai_internal_error"
    assert run.metadata_sanitized["fallback_used"] is False
    assert run.metadata_sanitized["model_invoked"] is False
    assert run.metadata_sanitized["delegation_started"] is False


def test_lucio_simple_greeting_provider_auth_error_uses_safe_local_fallback(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    service.client = _AuthErrorLucioClient()
    session = service.create_session("Fallback")

    response = service.send(
        LucioAgentRequest(
            session_id=session.session_id,
            prompt="Salve lucio tudo bem?",
            operation_type="lucio_chat",
        )
    )

    assert response.status == "completed_with_warnings"
    assert response.route_decision.route == "direct_response"
    assert response.error_code == "openai_auth_error"
    assert "resposta local segura" in response.text
    assert response.delegation_id is None
    run = service.kernel.get_run(response.run_id)
    assert run is not None
    assert run.metadata_sanitized["provider_error"] == "openai_auth_error"
    assert run.metadata_sanitized["fallback_used"] is True
    assert run.metadata_sanitized["fallback_type"] == "local_safe_chat"
    assert run.metadata_sanitized["model_invoked"] is False
    assert run.metadata_sanitized["local_execution_started"] is False
    assert run.metadata_sanitized["tool_invoked"] is False
    assert run.metadata_sanitized["delegation_started"] is False
    events = {event.event_type for event in service.kernel.list_run_events(response.run_id, include_hidden=True)}
    assert "lucio_safe_local_fallback_used" in events
    assert "lucio_local_tool_completed" not in events
    assert "test-key-never-exposed" not in str(run.metadata_sanitized)
    health = service.health()["config"]
    assert health["last_provider_error"] == "openai_auth_error"
    assert health["last_provider_error_at"]


def test_lucio_trivial_fact_provider_auth_error_uses_safe_local_fallback(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    service.client = _AuthErrorLucioClient()
    session = service.create_session("Trivia")

    response = service.send(
        LucioAgentRequest(
            session_id=session.session_id,
            prompt="Qual a cor do cavalo branco de Napoleao?",
            operation_type="lucio_chat",
        )
    )

    assert response.status == "completed_with_warnings"
    assert response.text == "Branco."
    run = service.kernel.get_run(response.run_id)
    assert run is not None
    assert run.metadata_sanitized["fallback_category"] == "trivial_low_risk_fact"
    assert run.metadata_sanitized["provider_error"] == "openai_auth_error"
    assert run.metadata_sanitized["delegation_started"] is False


def test_lucio_nontrivial_question_provider_auth_error_returns_provider_unavailable(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    service.client = _AuthErrorLucioClient()
    session = service.create_session("Nontrivial")

    response = service.send(
        LucioAgentRequest(
            session_id=session.session_id,
            prompt="Explique profundamente a arquitetura de X com fontes recentes.",
            operation_type="strategic_analysis",
        )
    )

    assert response.status == "completed_with_warnings"
    assert response.error_code == "openai_auth_error"
    assert "Nao vou inventar" in response.text
    assert response.delegation_id is None
    run = service.kernel.get_run(response.run_id)
    assert run is not None
    assert run.metadata_sanitized["status"] == "provider_unavailable"
    assert run.metadata_sanitized["fallback_used"] is False
    assert run.metadata_sanitized["local_execution_started"] is False
    assert run.metadata_sanitized["tool_invoked"] is False
    assert run.metadata_sanitized["delegation_started"] is False


def test_lucio_operational_request_does_not_use_chat_fallback(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch)
    service.client = _AuthErrorLucioClient()
    session = service.create_session("Operational")

    response = service.send(
        LucioAgentRequest(
            session_id=session.session_id,
            prompt="Crie reports/teste.md.",
            operation_type="lucio_chat",
            workspace_id="workspace_test",
            requested_capabilities=["create_file"],
        )
    )

    assert response.status in {"delegation_running", "pending_approval", "blocked"}
    run = service.kernel.get_run(response.run_id)
    assert run is not None
    assert run.metadata_sanitized.get("fallback_used") is not True
    events = {event.event_type for event in service.kernel.list_run_events(response.run_id, include_hidden=True)}
    assert "lucio_safe_local_fallback_used" not in events


def test_openai_internal_server_error_has_specific_safe_code():
    class InternalServerError(Exception):
        pass

    error_code = _safe_error_code(
        InternalServerError("Error code: 500 - Internal server error")
    )

    assert error_code == "openai_internal_error"
