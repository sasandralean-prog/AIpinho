from __future__ import annotations

import zipfile

from aipinho.app_factory import create_app
from aipinho.api.routers import governance_lifecycle_router
from aipinho.services.governance.lifecycle import canonical_public_chat_service as canonical_chat_module
from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.schemas.chat.chat_trace import ChatTraceItem
from aipinho.services.artifacts.artifact_interaction_core import ArtifactDownloadService
from fastapi.testclient import TestClient


class _FakeChatService:
    def respond(self, request) -> ChatResponse:
        return ChatResponse(
            response_id="chat_test_fake_response",
            session_id=None,
            status="ok",
            message="4",
            intent={
                "intent_type": "conversation",
                "requires_task": False,
                "requires_workspace": False,
                "requires_patch": False,
            },
            policy={"approval_required_for": []},
            trace=[
                ChatTraceItem(
                    stage="model_selected",
                    status="ok",
                    reason="test_profile_fake_provider",
                    source="test_provider/fake_provider",
                    data={
                        "role_id": "speaker",
                        "requested_capability": "conversation",
                        "candidate_models": ["fake_provider.chat"],
                        "gate_decision": "allowed_for_test_profile",
                        "selected_model": "fake_provider.chat",
                        "provider": "test_provider/fake_provider",
                        "fallback_used": False,
                        "stub_used": False,
                        "evaluation_status": "test_profile",
                        "final_message_id": "chat_test_fake_response",
                    },
                ),
                ChatTraceItem(
                    stage="model_run_completed",
                    status="ok",
                    reason="test_profile_deterministic_response",
                    source="test_provider/fake_provider",
                    data={"latency_ms": 1, "tokens": 1},
                ),
            ],
            model_used="fake_provider.chat",
            real_inference=False,
            evaluation_status="test_profile",
            fallback_used=False,
            citation_map={},
        )


class _HealthyRuntimeStateHygieneService:
    def queue_health(self) -> dict[str, object]:
        return {"backpressure_required": False}


def _use_fake_chat_service(monkeypatch) -> None:
    monkeypatch.setattr(canonical_chat_module, "ChatService", lambda: _FakeChatService())
    monkeypatch.setattr(governance_lifecycle_router, "RuntimeStateHygieneService", lambda: _HealthyRuntimeStateHygieneService())


class _FakeFiveChatService(_FakeChatService):
    def respond(self, request) -> ChatResponse:
        response = super().respond(request)
        return response.model_copy(update={"message": "5"})


def _use_fake_five_chat_service(monkeypatch) -> None:
    monkeypatch.setattr(canonical_chat_module, "ChatService", lambda: _FakeFiveChatService())
    monkeypatch.setattr(governance_lifecycle_router, "RuntimeStateHygieneService", lambda: _HealthyRuntimeStateHygieneService())


def test_persistent_chat_permission_status_uses_config_without_task() -> None:
    client = TestClient(create_app())
    session = client.post("/api/v1/chat/sessions", json={"title": "Permission status"}).json()["session"]
    session_id = session["session_id"]

    sent = client.post(
        f"/api/v1/chat/sessions/{session_id}/send",
        json={
            "content": (
                "Liste os diretorios/workspaces que a AIpinho tem permissao para ler, "
                "escrever, gerar artifact e usar shell/network governado."
            )
        },
    )

    assert sent.status_code == 200
    payload = sent.json()
    response = payload["chat_response"]
    assert response["status"] == "ok"
    assert response["operation_type"] == "permission_status"
    assert response["intent"]["intent_type"] == "permission_status"
    assert response["intent"]["requires_task"] is False
    assert response["intent"]["requires_workspace"] is False
    assert response["task_id"] is None
    assert response["task_preview_id"] is None
    assert "C:\\Dev\\AIpinho" in response["message"]
    assert "config/workspaces/workspace_registry.yaml" in response["message"]
    assert payload["assistant_message"]["metadata"]["operation_type"] == "permission_status"
    assert payload["assistant_message"]["metadata"]["requires_task"] == "False"


def test_mobile_chat_send_persists_user_and_assistant_without_task_or_raw(monkeypatch) -> None:
    _use_fake_chat_service(monkeypatch)
    client = TestClient(create_app())
    session = client.post("/api/v1/chat/sessions", json={"title": "Mobile persistent chat"}).json()["session"]
    session_id = session["session_id"]

    sent = client.post(f"/api/v1/chat/sessions/{session_id}/send", json={"content": "Quanto é 2+2?"})

    assert sent.status_code == 200
    payload = sent.json()
    assert payload["status"] == "ok"
    assert payload["user_message"]["role"] == "user"
    assert payload["assistant_message"]["role"] == "assistant"
    assert payload["user_message"]["task_id"] is None
    assert payload["assistant_message"]["task_id"] is None
    assert payload["user_message"]["raw_available"] is False
    assert payload["assistant_message"]["raw_available"] is False
    assert payload["assistant_message"]["metadata"]["approval_required"] == "False"
    assert payload["assistant_message"]["metadata"]["rag_used"] == "False"
    assert payload["chat_response"]["intent"]["intent_type"] == "conversation"
    assert payload["chat_response"]["intent"]["requires_task"] is False
    assert payload["chat_response"]["message"] == "4"
    assert payload["chat_response"]["model_used"] == "fake_provider.chat"
    assert payload["chat_response"]["real_inference"] is False
    assert payload["chat_response"]["fallback_used"] is False
    assert payload["chat_response"]["trace"][0]["source"] == "test_provider/fake_provider"
    assert payload["chat_response"]["trace"][0]["data"]["provider"] == "test_provider/fake_provider"
    assert payload["chat_response"]["trace"][0]["data"]["stub_used"] is False

    timeline = client.get(f"/api/v1/chat/sessions/{session_id}/timeline").json()["timeline"]
    assert [message["role"] for message in timeline["messages"][-2:]] == ["user", "assistant"]


def test_mobile_chat_view_model_uses_humanized_cards_for_persisted_messages(monkeypatch) -> None:
    _use_fake_chat_service(monkeypatch)
    client = TestClient(create_app())
    session_id = client.post("/api/v1/chat/sessions", json={"title": "Humanized mobile chat"}).json()["session"]["session_id"]
    client.post(f"/api/v1/chat/sessions/{session_id}/send", json={"content": "Quanto é 2+2?"})

    response = client.get(f"/api/v1/mobile/view-model/chat/{session_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"]["raw_default_visible"] is False
    assert payload["session_id"] == session_id
    message_cards = [card for card in payload["cards"] if card["card_type"] == "chat_message"]
    assert {card["metadata"]["role"] for card in message_cards} >= {"user", "assistant"}
    assistant_cards = [card for card in message_cards if card["metadata"]["role"] == "assistant"]
    assert assistant_cards
    assistant = assistant_cards[-1]
    assert assistant["answers"]["what_is_happening"]
    assert assistant["answers"]["why_is_it_happening"]
    assert assistant["answers"]["is_it_safe"]["answer"] in {"safe", "caution"}
    assert assistant["metadata"]["task_id"] == "null"
    assert assistant["metadata"]["approval_required"] == "False"
    assert assistant["metadata"]["rag_used"] == "False"
    assert assistant["copy"]["raw_available"] is False


def test_mobile_chat_presentation_mapper_renders_simple_chat_without_technical_keys(monkeypatch) -> None:
    _use_fake_five_chat_service(monkeypatch)
    client = TestClient(create_app())
    session_id = client.post("/api/v1/chat/sessions", json={"title": "Clean mobile presentation"}).json()["session"]["session_id"]
    prompt = "Quanto \u00e9 2 + 3?"
    client.post(f"/api/v1/chat/sessions/{session_id}/send", json={"content": prompt})

    response = client.get(f"/api/v1/mobile/view-model/chat/{session_id}")

    assert response.status_code == 200
    payload = response.json()
    presentation = payload["presentation"]
    assert presentation["raw_default_visible"] is False
    assert [message["role"] for message in presentation["messages"][-2:]] == ["user", "assistant"]
    assert presentation["messages"][-2]["label"] == "Você"
    assert presentation["messages"][-2]["text"] == prompt
    assert presentation["messages"][-1]["label"] == "AIpinho"
    assert presentation["messages"][-1]["text"] == "5"
    assert any(detail["label"] == "Task" and detail["value"] == "Sem task" for detail in presentation["details"])
    assert any(detail["label"] == "RAG" and detail["value"] == "Não" for detail in presentation["details"])
    assert any(detail["label"] == "Memória" and detail["value"] == "Não" for detail in presentation["details"])
    assert any(detail["label"] == "Approval" and detail["value"] == "Não" for detail in presentation["details"])
    assert any(detail["label"] == "Segurança" and detail["value"] == "Seguro" for detail in presentation["details"])
    assert not [card for card in payload["cards"] if card["card_type"] == "context_decision"]
    assert not [card for card in payload["cards"] if card["card_type"] == "artifact_feedback"]
    serialized_presentation = str(presentation)
    assert "what_is_happening" not in serialized_presentation
    assert "endpoint_ref" not in serialized_presentation
    assert "side_effect" not in serialized_presentation
    assert "raw_default_visible" not in "\n".join(message["text"] for message in presentation["messages"])
    assert "ref_id': 'latest'" not in serialized_presentation


def test_artifact_request_with_grounded_answer_returns_downloadable_artifact(monkeypatch) -> None:
    _use_fake_chat_service(monkeypatch)
    client = TestClient(create_app())
    session_id = client.post("/api/v1/chat/sessions", json={"title": "Artifact offer"}).json()["session"]["session_id"]

    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/send",
        json={"content": "Gere um zip com resposta.txt contendo a resposta da pergunta simples."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["chat_response"]["status"] == "ok"
    assert payload["chat_response"]["message_type"] == "assistant_final_answer"
    assert payload["chat_response"]["is_final_answer"] is True
    assert payload["chat_response"]["requires_user_action"] is False
    assert payload["chat_response"]["artifact_id"].startswith("artifact_")
    assert payload["chat_response"]["artifact_links"]
    assert payload["chat_response"]["artifact_links"][0]["artifact_id"].startswith("artifact_")
    assert payload["chat_response"]["artifact_links"][0]["filename"] == "artifacts.zip"
    assert payload["chat_response"]["artifact_links"][0]["download_endpoint"].startswith("/api/v1/artifacts/")
    assert payload["chat_response"]["artifact_links"][0]["download_endpoint"].endswith("/download")
    assert "/summary-zip" not in payload["chat_response"]["artifact_links"][0]["download_endpoint"]
    assert payload["chat_response"]["artifact_links"][0]["requires_token"] is True
    assert payload["chat_response"]["artifact_links"][0]["size_bytes"] > 0
    assert payload["chat_response"]["artifact_links"][1]["filename"] == "resposta.txt"
    assert payload["chat_response"]["artifact_links"][1]["download_endpoint"].startswith("/api/v1/artifacts/")
    assert payload["chat_response"]["artifact_links"][1]["requires_token"] is True
    assert payload["assistant_message"]["metadata"]["message_type"] == "assistant_final_answer"
    assert payload["assistant_message"]["metadata"]["artifact_id"].startswith("artifact_")
    assert payload["assistant_message"]["metadata"]["artifact_filename"] == "artifacts.zip"
    assert payload["assistant_message"]["metadata"]["artifact_links_json"]

    view_model = client.get(f"/api/v1/mobile/view-model/chat/{session_id}")
    assert view_model.status_code == 200
    presentation = view_model.json()["presentation"]
    assistant = presentation["messages"][-1]
    assert assistant["role"] == "assistant"
    assert [artifact["filename"] for artifact in assistant["artifacts"]] == ["artifacts.zip", "resposta.txt"]
    assert all(artifact["artifact_id"].startswith("artifact_") for artifact in assistant["artifacts"])
    assert all(artifact["requires_token"] is True for artifact in assistant["artifacts"])
    assert all("/summary-zip" not in artifact["download_endpoint"] for artifact in assistant["artifacts"])


def test_filesystem_archive_request_packages_explicit_folder_and_file_without_model_text(monkeypatch, tmp_path) -> None:
    _use_fake_chat_service(monkeypatch)
    folder = tmp_path / "ProjetoExemplo"
    folder.mkdir()
    (folder / "README.md").write_text("# Projeto\n", encoding="utf-8")
    (folder / "src").mkdir()
    (folder / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
    (folder / ".env").write_text("TOKEN=secret-value\n", encoding="utf-8")
    extra = tmp_path / "nota.txt"
    extra.write_text("nota solta\n", encoding="utf-8")
    client = TestClient(create_app())
    session_id = client.post("/api/v1/chat/sessions", json={"title": "Filesystem archive"}).json()["session"]["session_id"]

    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/send",
        json={
            "content": (
                f'Solicito um arquivo pacote.zip contendo a pasta com todos os arquivos em "{folder}" '
                f'e o arquivo separado "{extra}".'
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    chat_response = payload["chat_response"]
    assert chat_response["status"] == "ok"
    assert chat_response["operation_type"] == "filesystem_archive_request"
    assert chat_response["intent"]["intent_type"] == "filesystem_archive_request"
    assert chat_response["intent"]["requires_task"] is False
    assert chat_response["intent"]["requires_patch"] is False
    assert chat_response["policy"]["read_only"] is True
    assert chat_response["policy"]["workspace_write"] is False
    assert chat_response["artifact_links"][0]["filename"] == "pacote.zip"
    assert chat_response["artifact_links"][0]["requires_token"] is True
    assert chat_response["artifact_links"][0]["size_bytes"] > 0
    assert "contexto fornecido" not in chat_response["message"].lower()
    assert "artifact_generated_from_filesystem_archive" in chat_response["warnings"]

    artifact_id = chat_response["artifact_links"][0]["artifact_id"]
    zip_path = ArtifactDownloadService().path(artifact_id)
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
    assert "ProjetoExemplo/README.md" in names
    assert "ProjetoExemplo/src/main.py" in names
    assert "nota.txt" in names
    assert "ProjetoExemplo/.env" not in names

    view_model = client.get(f"/api/v1/mobile/view-model/chat/{session_id}")
    assert view_model.status_code == 200
    assistant = view_model.json()["presentation"]["messages"][-1]
    assert assistant["role"] == "assistant"
    assert assistant["artifacts"][0]["artifact_id"] == artifact_id
    assert assistant["artifacts"][0]["filename"] == "pacote.zip"
    assert assistant["artifacts"][0]["download_endpoint"].startswith("/api/v1/artifacts/")
    assert "/summary-zip" not in assistant["artifacts"][0]["download_endpoint"]


def test_readonly_project_analysis_creates_preview_not_fake_summary(monkeypatch) -> None:
    _use_fake_chat_service(monkeypatch)
    client = TestClient(create_app())
    session_id = client.post("/api/v1/chat/sessions", json={"title": "Readonly project preview"}).json()["session"]["session_id"]

    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/send",
        json={"content": r"Analise o projeto C:\TesteAI sem alterar arquivos."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["chat_response"]["status"] == "preview"
    assert payload["chat_response"]["message_type"] == "task_preview"
    assert payload["chat_response"]["is_final_answer"] is False
    assert payload["chat_response"]["grounded"] is False
    assert payload["chat_response"]["grounding_missing_reason"] == "read_files_not_executed"
    assert "Ainda nao li arquivos" in payload["chat_response"]["message"]
    assert payload["assistant_message"]["metadata"]["message_type"] == "task_preview"
    assert payload["chat_response"]["session_id"] == session_id
    assert payload["assistant_message"]["metadata"]["operational_session_id"] == session_id
    assert payload["assistant_message"]["metadata"]["approval_required"] == "False"
    assert all("vision" not in action["type"] and "ocr" not in action["type"] for action in payload["chat_response"]["next_actions"])


def test_mobile_chat_send_processes_attached_artifacts_as_sanitized_context(monkeypatch) -> None:
    captured: list[str] = []

    class _AttachmentAwareChatService(_FakeChatService):
        def respond(self, request) -> ChatResponse:
            captured.append(request.message)
            return super().respond(request)

    monkeypatch.setattr(canonical_chat_module, "ChatService", lambda: _AttachmentAwareChatService())
    monkeypatch.setattr(governance_lifecycle_router, "RuntimeStateHygieneService", lambda: _HealthyRuntimeStateHygieneService())
    client = TestClient(create_app())
    session_id = client.post("/api/v1/chat/sessions", json={"title": "Attached artifact"}).json()["session"]["session_id"]
    upload = client.post(
        "/api/v1/artifacts/upload",
        json={"filename": "contexto.txt", "content": "conteudo seguro do anexo", "content_type": "text/plain"},
    ).json()["upload"]
    artifact_id = upload["artifact"]["artifact_id"]

    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/send",
        json={"content": "Explique o anexo enviado.", "metadata": {"attached_artifact_ids": [artifact_id]}},
    )

    assert response.status_code == 200
    payload = response.json()
    assert any("conteudo seguro do anexo" in item for item in captured)
    assert payload["chat_response"]["intent"]["attached_artifact_ids"] == [artifact_id]
    assert payload["assistant_message"]["metadata"]["attached_artifact_count"] == "1"
    assert payload["chat_response"]["evidence_refs"][0]["type"] == "artifact"


def test_followup_without_grounded_result_does_not_invent_summary(monkeypatch) -> None:
    _use_fake_chat_service(monkeypatch)
    client = TestClient(create_app())
    session_id = client.post("/api/v1/chat/sessions", json={"title": "No grounded result"}).json()["session"]["session_id"]

    response = client.post(f"/api/v1/chat/sessions/{session_id}/send", json={"content": "Mostre novamente o resumo anterior."})

    assert response.status_code == 200
    payload = response.json()
    assert payload["chat_response"]["status"] == "degraded"
    assert payload["chat_response"]["message_type"] == "assistant_degraded_answer"
    assert payload["chat_response"]["is_final_answer"] is False
    assert payload["chat_response"]["grounding_missing_reason"] == "no_indexed_final_result"
    assert "nao tenho um resumo real" in payload["chat_response"]["message"]

    view_model = client.get(f"/api/v1/mobile/view-model/chat/{session_id}")
    assert view_model.status_code == 200
    mobile = view_model.json()
    assistant_cards = [
        card
        for card in mobile["cards"]
        if card["card_type"] == "chat_message" and card["metadata"]["role"] == "assistant"
    ]
    assert assistant_cards[-1]["status"] == "degraded"
    assert assistant_cards[-1]["severity"] == "warning"
    assert assistant_cards[-1]["answers"]["is_it_safe"]["answer"] == "caution"
    assert mobile["presentation"]["messages"][-1]["safety_label"] == "Atenção"
    assert any(
        detail["label"] == "Segurança" and detail["value"] == "Atenção: resposta degradada"
        for detail in mobile["presentation"]["details"]
    )


def test_followup_reuses_indexed_final_answer(monkeypatch) -> None:
    _use_fake_chat_service(monkeypatch)
    client = TestClient(create_app())
    session_id = client.post("/api/v1/chat/sessions", json={"title": "Grounded recall"}).json()["session"]["session_id"]
    client.post(f"/api/v1/chat/sessions/{session_id}/send", json={"content": "Quanto e 2+2?"})

    response = client.post(f"/api/v1/chat/sessions/{session_id}/send", json={"content": "Repita a resposta anterior."})

    assert response.status_code == 200
    payload = response.json()
    assert payload["chat_response"]["status"] == "ok"
    assert payload["chat_response"]["message_type"] == "assistant_final_answer"
    assert payload["chat_response"]["message"] == "4"
    assert payload["chat_response"]["result_ref_id"].startswith("result_")
    assert payload["chat_response"]["evidence_refs"][0]["type"] == "chat_result"


def test_summary_followup_does_not_recall_simple_answer_or_project_preview(monkeypatch) -> None:
    _use_fake_chat_service(monkeypatch)
    client = TestClient(create_app())
    session_id = client.post("/api/v1/chat/sessions", json={"title": "Summary recall scope"}).json()["session"]["session_id"]
    client.post(f"/api/v1/chat/sessions/{session_id}/send", json={"content": "Quanto e 2+2?"})
    client.post(
        f"/api/v1/chat/sessions/{session_id}/send",
        json={"content": r"Analise o projeto C:\ProjetoExemplo sem alterar arquivos."},
    )

    response = client.post(f"/api/v1/chat/sessions/{session_id}/send", json={"content": "Pode repetir o resumo?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["chat_response"]["status"] == "degraded"
    assert payload["chat_response"]["message_type"] == "assistant_degraded_answer"
    assert payload["chat_response"]["grounding_missing_reason"] == "no_indexed_final_result"
    assert "nao tenho um resumo real" in payload["chat_response"]["message"]
    assert payload["chat_response"]["message"] != "4"


def test_summary_followup_can_recall_grounded_session_diagnostic(monkeypatch) -> None:
    _use_fake_chat_service(monkeypatch)
    client = TestClient(create_app())
    session_id = client.post("/api/v1/chat/sessions", json={"title": "Grounded diagnostic recall"}).json()["session"]["session_id"]
    diagnostic = client.post(
        f"/api/v1/chat/sessions/{session_id}/send",
        json={"content": "Diagnostique o bug na timeline da conversa truncada."},
    ).json()["chat_response"]

    response = client.post(f"/api/v1/chat/sessions/{session_id}/send", json={"content": "Pode repetir o resumo?"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["chat_response"]["status"] == "ok"
    assert payload["chat_response"]["message"] == diagnostic["message"]
    assert payload["chat_response"]["result_ref_id"].startswith("result_")


def test_session_diagnostic_is_structured_and_does_not_call_llm(monkeypatch) -> None:
    _use_fake_chat_service(monkeypatch)
    client = TestClient(create_app())
    session_id = client.post("/api/v1/chat/sessions", json={"title": "Session diagnostic"}).json()["session"]["session_id"]

    response = client.post(
        f"/api/v1/chat/sessions/{session_id}/send",
        json={"content": "Diagnostique a timeline da conversa e a resposta truncada."},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["chat_response"]["message_type"] == "system_diagnostic_result"
    assert payload["chat_response"]["operation_type"] == "session_diagnostic"
    assert payload["chat_response"]["real_inference"] is None
    assert payload["assistant_message"]["metadata"]["message_type"] == "system_diagnostic_result"
