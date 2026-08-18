from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from aipinho.api.routers import continue_integration_router
from aipinho.core.paths import PATHS
from aipinho.main import app


client = TestClient(app)


def _chat_payload(prompt: str, *, model: str = "aipinho-local", stream: bool = False) -> dict:
    return {
        "model": model,
        "stream": stream,
        "messages": [{"role": "user", "content": prompt}],
    }


def test_get_v1_models_returns_aipinho_models():
    response = client.get("/v1/models")
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "list"
    model_ids = {item["id"] for item in data["data"]}
    assert {"aipinho-local", "aipinho-agent"} <= model_ids


def test_post_v1_chat_completions_simple_message_returns_openai_compatible_response():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Responda apenas: AIpinho conectada."),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["object"] == "chat.completion"
    assert data["model"] == "aipinho-local"
    assert data["choices"][0]["message"] == {"role": "assistant", "content": "AIpinho conectada."}
    assert data["choices"][0]["finish_reason"] == "stop"


def test_continue_route_does_not_call_openai(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-value-that-must-not-be-used")
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Responda apenas: rota local."),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["choices"][0]["message"]["content"] == "rota local."
    assert data["aipinho"]["route"] == "continue_openai_compat"


def test_continue_route_works_with_openai_disabled(monkeypatch):
    monkeypatch.setenv("OPENAI_ENABLED", "false")
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Responda apenas: sem OpenAI."),
    )
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "sem OpenAI."


def test_continue_route_blocks_write_shell_in_connection_phase():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Crie um arquivo chamado teste.txt e execute um comando shell para validar."),
    )
    assert response.status_code == 200
    data = response.json()
    content = data["choices"][0]["message"]["content"]
    assert "APPROVAL REQUIRED" in content
    assert data["aipinho"]["approval_id"].startswith("approval_")
    assert data["aipinho"]["execution_allowed"] is False
    assert data["aipinho"]["reason_code"] == "continue_approval_required"
    assert data["aipinho"]["operation_contract"]["source_channel"] == "vscode_continue"


def test_unknown_model_returns_clear_error():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Ola", model="unknown-model"),
    )
    assert response.status_code == 400
    detail = response.json()["detail"]["error"]
    assert detail["code"] == "model_not_found"
    assert "aipinho-local" in detail["available_models"]


def test_malformed_body_returns_422_or_structured_error():
    response = client.post("/v1/chat/completions", json={"model": "aipinho-local"})
    assert response.status_code in {400, 422}


def test_stream_true_returns_sse_chunks():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Responda apenas: resposta em stream.", stream=True),
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "chat.completion.chunk" in response.text
    assert '"delta": {"role": "assistant"}' in response.text
    assert '"content": "resposta em stream."' in response.text


def test_stream_true_finishes_with_done():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Responda apenas: fim.", stream=True),
    )
    assert response.status_code == 200
    assert response.text.rstrip().endswith("data: [DONE]")


def test_continue_simple_ola_smoke_returns_response():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Responda apenas: Ola."),
    )
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "Ola."


def test_continue_adapter_does_not_pass_external_model_alias_to_internal_chat_service(monkeypatch):
    captured = {}

    class FakeChatService:
        def respond(self, request):
            captured["model_id"] = request.model_id
            return SimpleNamespace(message="ok")

    monkeypatch.setattr(continue_integration_router, "ChatService", FakeChatService)
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Ola"),
    )
    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "ok"
    assert captured["model_id"] is None


def test_continue_vscode_execute_route_is_disabled_in_connection_phase():
    response = client.post(
        "/v1/integrations/vscode/actions/execute",
        json={"source": "vscode_continue", "approval_id": "approval_example"},
    )
    assert response.status_code == 403
    assert response.json()["detail"]["reason_code"] == "continue_connection_phase_no_write_or_shell"


def test_continue_route_does_not_write_files(tmp_path: Path):
    target = tmp_path / "continue_should_not_write.txt"
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload(f"Crie o arquivo {target} com conteudo teste."),
    )
    assert response.status_code == 200
    assert not target.exists()
    data = response.json()
    assert data["aipinho"]["reason_code"] == "continue_approval_required"
    assert data["aipinho"]["approval_id"].startswith("approval_")


def test_continue_route_does_not_run_shell():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Execute o comando echo teste no terminal."),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["aipinho"]["reason_code"] == "continue_approval_required"
    assert data["aipinho"]["approval_id"].startswith("approval_")


def test_continue_math_2_plus_2_responds_4():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("quanto e 2+2?"),
    )
    assert response.status_code == 200
    data = response.json()
    assert "4" in data["choices"][0]["message"]["content"]
    assert data["aipinho"]["continue_intent"] == "math_or_reasoning"


def test_continue_personality_question_is_not_operational_refusal():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Voce consegue configurar personalidade e tom?"),
    )
    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    assert "conversa segura" not in content
    assert "configuracao" in content.lower() or "orientar" in content.lower()


def test_continue_how_to_enable_features_returns_configuration_guidance():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Como eu posso configurar para liberar estes recursos da rota compativel?"),
    )
    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    assert "CONTINUE_MODE" in content
    assert "CONTINUE_ALLOW_PATCH_PREVIEW" in content
    assert "conversa segura" not in content


def test_continue_can_read_files_answer_is_capability_aware_not_false_incapable():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Voce consegue ler arquivos?"),
    )
    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    assert "arquivos que o Continue anexar" in content
    assert "Nao consigo ler arquivos" not in content
    assert "não consigo ler arquivos" not in content


def test_continue_agent_mode_answer_explains_context_vs_governed_tools():
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "aipinho-local",
            "stream": False,
            "messages": [
                {"role": "system", "content": "You are in Agent Mode. Use apply only when explicitly approved."},
                {"role": "user", "content": "Voce consegue ler arquivos e alterar arquivos?"},
            ],
        },
    )
    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    assert "Continue anexar" in content
    assert "preview, approval" in content


def test_continue_context_items_are_detected():
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "aipinho-local",
            "messages": [
                {"role": "system", "content": "@rules/aipinho-rules.md"},
                {"role": "user", "content": "@App.tsx\n@Terminal\n@Git Diff\nExplique este contexto."},
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    item_names = {item["name"] for item in data["aipinho"]["context_items"]}
    assert {"rules/aipinho-rules.md", "App.tsx", "Terminal", "Git Diff"} <= item_names


def test_continue_app_tsx_context_can_be_analyzed_without_file_tool():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("@App.tsx\nexport function App() { return <div /> }\nExplique este arquivo."),
    )
    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    assert "Recebi contexto anexado pelo Continue" in content
    assert "App.tsx" in content


def test_continue_terminal_context_can_be_summarized():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("@Terminal\nnpm test failed\nExplique este erro no terminal."),
    )
    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    assert "terminal" in content.lower()
    assert "Recebi contexto" in content


def test_continue_git_diff_context_can_be_summarized():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("@Git Diff\ndiff --git a/App.tsx b/App.tsx\nExplique este diff."),
    )
    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    assert "git diff" in content.lower()


def test_continue_rules_context_does_not_trigger_refusal():
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "aipinho-local",
            "messages": [
                {"role": "system", "content": "@rules/new-rule.md\nUse tom tecnico."},
                {"role": "user", "content": "Explique as regras anexadas."},
            ],
        },
    )
    assert response.status_code == 200
    content = response.json()["choices"][0]["message"]["content"]
    assert "conversa segura" not in content


def test_continue_write_request_creates_preview_or_approval_not_direct_write():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Altere App.tsx para mostrar Hello."),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["aipinho"]["continue_intent"] == "file_write_request"
    assert data["aipinho"]["reason_code"] == "continue_approval_required"
    assert data["aipinho"]["approval_id"].startswith("approval_")
    assert data["aipinho"]["operation_contract"]["operation_type"] == "write_files"
    assert "APPROVAL REQUIRED" in data["choices"][0]["message"]["content"]


def test_vscode_continue_text_approval_works_for_created_approval():
    create_response = client.post(
        "/v1/chat/completions",
        json={
            **_chat_payload("Altere App.tsx para mostrar Hello."),
            "user": "approval-flow-test",
        },
    )
    assert create_response.status_code == 200
    approval_id = create_response.json()["aipinho"]["approval_id"]

    approve_response = client.post(
        "/v1/chat/completions",
        json={
            **_chat_payload(f"APROVAR {approval_id}"),
            "user": "approval-flow-test",
        },
    )

    assert approve_response.status_code == 200
    data = approve_response.json()
    assert data["aipinho"]["approval_command"] is True
    assert data["aipinho"]["approval_id"] == approval_id
    assert "Approval registrado" in data["choices"][0]["message"]["content"]


def test_chat_approval_command_endpoint_works_for_created_approval():
    create_response = client.post(
        "/v1/chat/completions",
        json={
            **_chat_payload("Altere App.tsx para mostrar Hello."),
            "user": "approval-endpoint-test",
        },
    )
    assert create_response.status_code == 200
    approval_id = create_response.json()["aipinho"]["approval_id"]

    command_response = client.post(
        "/api/v1/chat/approval-command",
        json={
            "session_id": "continue_approval-endpoint-test",
            "text": f"NEGAR {approval_id}",
            "source_channel": "test_harness",
        },
    )

    assert command_response.status_code == 200
    data = command_response.json()
    assert data["status"] == "ok"
    assert "Approval encerrado" in data["message"]
    assert data["chat_response"]["approval_id"] == approval_id


def test_continue_shell_request_creates_preview_or_approval_not_direct_shell():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Rode npm test no terminal."),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["aipinho"]["continue_intent"] == "shell_request"
    assert data["aipinho"]["reason_code"] == "continue_approval_required"
    assert data["aipinho"]["approval_id"].startswith("approval_")
    assert data["aipinho"]["operation_contract"]["operation_type"] == "run_command"


def test_continue_delete_request_requires_strong_approval():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Delete o arquivo antigo App.tsx."),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["aipinho"]["continue_intent"] in {"dangerous_operation_request", "file_write_request"}
    assert "approval" in data["choices"][0]["message"]["content"]


def test_continue_generic_operational_refusal_only_for_unsupported_operations():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Como configuro personalidade e tom?"),
    )
    assert response.status_code == 200
    assert "rota OpenAI-compatible do Continue esta habilitada apenas para conexao" not in response.json()["choices"][0]["message"]["content"]


def test_continue_streaming_never_returns_blank_for_simple_answer():
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("quanto e 2+2?", stream=True),
    )
    assert response.status_code == 200
    assert '"content": "2+2 = 4."' in response.text
    assert response.text.rstrip().endswith("data: [DONE]")


def test_continue_code_generation_question_is_not_file_write_refusal(monkeypatch):
    class FakeChatService:
        def respond(self, request):
            return SimpleNamespace(message="def soma(a, b):\n    return a + b")

    monkeypatch.setattr(continue_integration_router, "ChatService", FakeChatService)
    response = client.post(
        "/v1/chat/completions",
        json=_chat_payload("Crie uma funcao Python que soma dois numeros."),
    )
    assert response.status_code == 200
    data = response.json()
    assert "def soma" in data["choices"][0]["message"]["content"]
    assert data["aipinho"]["continue_intent"] == "conversation"
    assert "reason_code" not in data["aipinho"]


def test_port_documentation_matches_actual_adapter_port():
    doc = (PATHS.project_root / "docs" / "integrations" / "continue_vscode_aipinho.md").read_text(encoding="utf-8")
    assert "http://127.0.0.1:9088/v1" in doc
    assert "http://127.0.0.1:8088/v1" not in doc
