from __future__ import annotations

from pathlib import Path

from aipinho.schemas.gemini_executor import GeminiExecutorRequest
from aipinho.services.gemini_executor.gemini_executor_client import FakeGeminiClient
from aipinho.services.gemini_executor.gemini_executor_config_service import GeminiExecutorConfigService
from aipinho.services.gemini_executor.gemini_executor_service import GeminiExecutorService
from aipinho.services.gemini_executor.gemini_executor_session_store import GeminiExecutorSessionStore


def _service(tmp_path: Path, monkeypatch, *, enabled: bool = True, allow_write: bool = False, allow_shell: bool = False) -> GeminiExecutorService:
    monkeypatch.setenv("GEMINI_EXECUTOR_ENABLED", "true" if enabled else "false")
    monkeypatch.setenv("GEMINI_EXECUTOR_ALLOW_WRITE", "true" if allow_write else "false")
    monkeypatch.setenv("GEMINI_EXECUTOR_ALLOW_SHELL", "true" if allow_shell else "false")
    monkeypatch.setenv("GEMINI_EXECUTOR_DEFAULT_MODEL", "gemini-test-model")
    monkeypatch.setenv("AIPINHO_GEMINI_EXECUTOR_ROOT", str(tmp_path / "gemini_store"))
    monkeypatch.setenv("AIPINHO_AGENT_KERNEL_ROOT", str(tmp_path / "agent_kernel"))
    monkeypatch.setenv("AIPINHO_AGENT_DELEGATION_ROOT", str(tmp_path / "delegations"))
    monkeypatch.setenv("AIPINHO_AGENT_MEMORY_ROOT", str(tmp_path / "memory"))
    monkeypatch.setenv("AIPINHO_POLICY_KERNEL_ROOT", str(tmp_path / "policy"))
    monkeypatch.setenv("AIPINHO_EVENT_STORE_ROOT", str(tmp_path / "events"))
    monkeypatch.setenv("AIPINHO_EVENT_RAW_ROOT", str(tmp_path / "raw"))
    monkeypatch.setenv("AIPINHO_EVENT_AUDIT_ROOT", str(tmp_path / "audit"))
    service = GeminiExecutorService(
        config_service=GeminiExecutorConfigService(policy_path=tmp_path / "missing.yaml"),
        session_store=GeminiExecutorSessionStore(tmp_path / "gemini_store"),
        client=FakeGeminiClient(),
    )
    service._publish = lambda *args, **kwargs: None
    return service


def test_disabled_executor_returns_blocked_without_provider_call(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch, enabled=False)
    session = service.create_session()
    response = service.send(GeminiExecutorRequest(session_id=session.session_id, prompt="ola"))

    assert response.status == "blocked"
    assert response.error_code == "gemini_executor_policy_blocked"


def test_successful_fake_chat_uses_separate_gemini_namespace(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch, enabled=True)
    session = service.create_session()
    response = service.send(GeminiExecutorRequest(session_id=session.session_id, prompt="Explique uma interface."))

    assert response.status == "completed"
    assert response.provider == "gemini"
    assert response.model == "gemini-test-model"
    assert response.run_id
    assert f"run:{response.run_id}" in response.evidence_refs
    messages = service.messages(session.session_id)
    assert [message.role for message in messages] == ["user", "assistant"]
    assert all(message.session_id.startswith("gemini_session_") for message in messages)


def test_local_request_delegates_to_aipinho_with_parent_child_trace(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch, enabled=True)
    session = service.create_session()

    response = service.send(
        GeminiExecutorRequest(
            session_id=session.session_id,
            prompt="Analise o workspace autorizado.",
            operation_type="readonly_analysis",
            workspace_id="workspace_test",
            requested_capabilities=["read_workspace"],
        )
    )

    assert response.status == "delegation_running"
    assert response.delegation_id
    assert response.child_run_id
    parent = service.agent_kernel.get_run(response.run_id)
    child = service.agent_kernel.get_run(response.child_run_id)
    assert parent is not None
    assert child is not None
    assert parent.agent_id == "gemini"
    assert child.agent_id == "aipinho"
    assert child.parent_run_id == parent.run_id
    assert child.delegation_id == response.delegation_id
    assert {event["event_type"] for event in service.events(parent.run_id)} >= {
        "delegation_created",
        "delegation_child_run_started",
        "gemini_delegation_created",
    }


def test_gemini_delegation_operation_uses_capability_aliases(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch, enabled=True)
    session = service.create_session()

    response = service.send(
        GeminiExecutorRequest(
            session_id=session.session_id,
            prompt="Gere um artifact governado com resumo curto.",
            operation_type="gemini_chat",
            requested_capabilities=["read_workspace", "create_artifact", "delegate"],
        )
    )

    assert response.status == "delegation_running"
    assert response.delegation_id
    child = service.agent_kernel.get_run(response.child_run_id)
    assert child is not None
    assert child.operation_type == "artifact_request"


def test_gemini_delegation_large_operational_request_does_not_become_plain_artifact_request(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch, enabled=True, allow_write=True, allow_shell=True)
    session = service.create_session()

    response = service.send(
        GeminiExecutorRequest(
            session_id=session.session_id,
            prompt="Analyze a project, propose fixes, generate artifacts, build and test through governed execution.",
            operation_type="gemini_chat",
            workspace_id="workspace_test",
            requested_capabilities=["scan_workspace", "create_file", "workspace_write", "create_artifact", "run_shell_build", "run_tests", "validation"],
        )
    )

    assert response.status == "delegation_running"
    assert response.delegation_id
    child = service.agent_kernel.get_run(response.child_run_id)
    assert child is not None
    assert child.operation_type == "delegated_governed_execution"
    assert child.operation_type != "artifact_request"


def test_blocked_delegation_with_no_child_run_has_truthful_message(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch, enabled=True)
    service.policy.evaluate = lambda **kwargs: {
        "allowed": True,
        "reasons": [],
        "requires_approval": False,
        "workspace": {"status": "allowed"},
        "blocked_capabilities": [],
    }
    session = service.create_session()

    response = service.send(
        GeminiExecutorRequest(
            session_id=session.session_id,
            prompt="Request unsupported local vision pipeline.",
            operation_type="gemini_chat",
            workspace_id="workspace_test",
            requested_capabilities=["read_workspace", "vision_pipeline"],
        )
    )

    assert response.status == "blocked"
    assert response.child_run_id is None
    assert "nao iniciou execucao real" in response.text
    assert "Nenhum child run foi criado" in response.text
    assert "Vou usar os eventos do child run" not in response.text


def test_mobile_view_model_keeps_raw_hidden_and_exposes_active_run(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch, enabled=True)
    session = service.create_session()
    response = service.send(GeminiExecutorRequest(session_id=session.session_id, prompt="Explique uma interface."))

    view_model = service.mobile_view_model(session.session_id)

    assert view_model["raw_default_visible"] is False
    assert view_model["cloud_warning_visible"] is True
    assert view_model["active_run"]["run_id"] == response.run_id
    assert [message["role"] for message in view_model["messages"]] == ["user", "assistant"]


def test_write_capability_is_blocked_when_gemini_write_disabled(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch, enabled=True, allow_write=False)
    session = service.create_session()
    response = service.send(
        GeminiExecutorRequest(
            session_id=session.session_id,
            prompt="Crie um patch.",
            requested_capabilities=["create_patch_preview"],
        )
    )

    assert response.status == "blocked"
    assert response.structured_actions[0].policy_decision["blocked_capabilities"] == ["create_patch_preview"]


def test_explicit_file_creation_delegates_after_request_enrichment(tmp_path, monkeypatch):
    workspace = tmp_path / "target"
    workspace.mkdir()
    service = _service(tmp_path, monkeypatch, enabled=True, allow_write=True)
    service.policy.evaluate = lambda **kwargs: {
        "allowed": True,
        "reasons": [],
        "requires_approval": True,
        "workspace": {"status": "allowed"},
        "blocked_capabilities": [],
    }
    session = service.create_session()

    response = service.send(
        GeminiExecutorRequest(
            session_id=session.session_id,
            prompt=f"Crie arquivo smoke.txt em {workspace} com conteudo ok",
        )
    )

    assert response.status == "delegation_running"
    assert response.delegation_id
    child = service.agent_kernel.get_run(response.child_run_id)
    assert child is not None
    assert child.operation_type == "workspace_operation"
    assert "write_workspace" in child.capabilities_requested


def test_preview_does_not_apply_patch_and_requires_governed_pipeline(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch, enabled=True, allow_write=True)
    session = service.create_session()
    response = service.preview(GeminiExecutorRequest(session_id=session.session_id, prompt="Gere preview de patch."))

    assert response.status == "preview_created"
    assert "Apply exige approval" in response.text
    assert any(action.requires_approval for action in response.structured_actions)


def test_api_key_values_never_appear_in_config_status(tmp_path, monkeypatch):
    for name in [
        "GEMINI_API_KEY",
        "GEMINI_API_KEY_PRIMARY",
        "GEMINI_API_KEY_SECONDARY",
        "GEMINI_API_KEYS",
        *[f"GEMINI_API_KEY_FALLBACK_{index}" for index in range(1, 21)],
    ]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY_PRIMARY", "SECRET_PRIMARY_VALUE")
    monkeypatch.setenv("GEMINI_API_KEY_SECONDARY", "SECRET_SECONDARY_VALUE")
    monkeypatch.setenv("GEMINI_API_KEY_FALLBACK_1", "SECRET_FALLBACK_VALUE")
    service = _service(tmp_path, monkeypatch, enabled=True)
    status = service.config_service.status().model_dump()

    assert status["primary_key_configured"] is True
    assert status["secondary_key_configured"] is True
    assert status["configured_key_count"] == 3
    assert status["fallback_key_count_configured"] == 1
    assert "SECRET_PRIMARY_VALUE" not in str(status)
    assert "SECRET_SECONDARY_VALUE" not in str(status)
    assert "SECRET_FALLBACK_VALUE" not in str(status)


def test_gemini_sessions_can_be_renamed_and_deleted_with_history(tmp_path, monkeypatch):
    service = _service(tmp_path, monkeypatch, enabled=True)
    session = service.create_session("Inicial")
    service.send(GeminiExecutorRequest(session_id=session.session_id, prompt="Ola"))

    renamed = service.rename_session(session.session_id, "Projeto")
    assert renamed is not None
    assert renamed.title == "Projeto"
    assert len(service.messages(session.session_id)) == 2

    assert service.delete_session(session.session_id) is True
    assert service.get_session(session.session_id) is None
