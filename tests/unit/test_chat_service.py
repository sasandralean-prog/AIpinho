from pathlib import Path

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.models.model_response import ModelResponse
from aipinho.services.chat.chat_service import ChatService
from aipinho.services.web_search_provider_service import WebSearchProviderService


class FakeUnavailableModelInvocationService:
    def invoke(self, request):
        return ModelResponse(
            request_id=request.request_id,
            model_id=request.model_id,
            provider_id=request.provider_id,
            status="error",
            content="",
            finish_reason="error",
            real_inference=False,
            warnings=["fake_runner_model_process_error"],
            metadata={"latency_ms": 1},
        )


class FakeConversationModelInvocationService:
    def __init__(self):
        self.last_request = None

    def invoke(self, request):
        self.last_request = request
        return ModelResponse(
            request_id=request.request_id,
            model_id="fake_provider.chat",
            provider_id="test_provider/fake_provider",
            status="completed",
            content="Conversa respondida pelo provider fake de teste.",
            finish_reason="stop",
            real_inference=True,
            warnings=[],
            metadata={"latency_ms": 1, "evaluation_status": "test_profile"},
        )


def test_chat_service_conversation_does_not_create_task():
    response = ChatService(model_invocation_service=FakeConversationModelInvocationService()).respond(
        ChatRequest(message="Bom dia, tudo certo?", include_trace=True)
    )
    assert response.status == "ok"
    assert response.intent["intent_type"] == "conversation"
    assert response.intent["requires_task"] is False
    assert response.contract_preview == {}
    assert response.model_used == "fake_provider.chat"
    assert response.real_inference is True
    assert response.fallback_used is False
    assert any(item.stage == "conversation_model_selection" for item in response.trace)


def test_chat_service_applies_normal_chat_runtime_policy():
    fake_invocation = FakeConversationModelInvocationService()
    response = ChatService(model_invocation_service=fake_invocation).respond(
        ChatRequest(message="Bom dia, tudo certo?", include_trace=True)
    )
    assert response.status == "ok"
    assert fake_invocation.last_request is not None
    assert fake_invocation.last_request.generation_config.max_tokens == 256
    assert fake_invocation.last_request.generation_config.temperature == 0.0
    assert fake_invocation.last_request.generation_config.top_p == 1.0
    assert fake_invocation.last_request.metadata["ctx_size"] == 8192
    assert fake_invocation.last_request.metadata["timeout_seconds"] == 20
    assert fake_invocation.last_request.metadata["output_contract_type"] == "plain_text"
    assert fake_invocation.last_request.model_id == "qwen3_1_7b_q6_k"
    policy_messages = [message for message in fake_invocation.last_request.messages if message.metadata.get("source") == "policy_decision"]
    assert policy_messages
    assert "safe_to_execute" in policy_messages[0].content
    assert "trace" not in policy_messages[0].content


def test_chat_service_preserves_explicit_model_override():
    fake_invocation = FakeConversationModelInvocationService()
    ChatService(model_invocation_service=fake_invocation).respond(
        ChatRequest(message="Bom dia, tudo certo?", model_id="explicit.test.model")
    )

    assert fake_invocation.last_request is not None
    assert fake_invocation.last_request.model_id == "explicit.test.model"


def test_chat_service_forbidden_root_blocked():
    response = ChatService().respond(ChatRequest(message=r"Corrija C:\Windows"))
    assert response.status == "blocked"
    assert response.intent["workspace"]["protected"] is True
    assert response.policy["safe_to_execute"] is False


def test_chat_service_artifact_is_preview_not_execution():
    response = ChatService().respond(ChatRequest(message="Salve um relatorio em reports/final.md"))
    assert response.status in {"preview", "needs_clarification"}
    assert response.intent["intent_type"] == "artifact_generation"
    assert "write_files" in response.policy["approval_required_for"]
    assert response.policy["safe_to_execute"] is False


def test_chat_service_patch_preview_only_creates_preview_without_apply_or_write():
    response = ChatService().respond(
        ChatRequest(
            message=r"Prepare um patch preview governado para o projeto C:\Users\rafae\Documents\AIpinhoTestes\Projeto. Ainda nao aplique.",
            mode="preview",
        )
    )

    assert response.status == "preview"
    assert response.preview_id
    assert response.task_id is None
    assert response.intent["requested_actions"] == ["patch_preview"]
    assert response.policy["allowed_actions"] == ["patch_preview"]
    assert response.policy["approval_required_for"] == []


def test_chat_service_audit_register_instruction_is_not_memory_candidate_request():
    service = ChatService()

    assert service._requests_memory_candidate("Registre os arquivos alterados e os comandos executados.") is False
    assert service._requests_memory_candidate("Guarde esta memoria com a causa e a fonte verificadas.") is True


def test_chat_service_chat_report_is_not_write():
    response = ChatService().respond(ChatRequest(message="Faca um report final desta conversa"))
    assert response.status == "ok"
    assert response.intent["intent_type"] == "in_chat_final_report"
    assert response.intent["requires_task"] is False
    assert response.policy["approval_required_for"] == []


def test_chat_service_empty_message_is_friendly_error():
    response = ChatService().respond(ChatRequest(message="   "))
    assert response.status == "error"
    assert "Mensagem vazia" in response.message


def test_chat_service_preview_mode_includes_trace():
    response = ChatService().respond(ChatRequest(message=r"Conserte o bug no projeto C:\Dev\AIpinho", mode="preview"))
    assert response.status == "preview"
    assert response.trace


def test_chat_service_model_process_failure_degrades_without_stub_fallback():
    response = ChatService(model_invocation_service=FakeUnavailableModelInvocationService()).respond(
        ChatRequest(message="quanto e 2+2?", include_trace=True)
    )
    assert response.status == "degraded"
    assert response.real_inference is False
    assert response.fallback_used is True
    assert response.model_used != "stub.default"
    assert "conversation_model_unavailable" in response.model_warnings
    assert any(item.stage == "conversation_model_selection" for item in response.trace)


def test_public_fact_query_calls_web_provider_and_includes_sources():
    provider = WebSearchProviderService(config={"enabled": True, "provider_id": "fake_web", "provider_type": "fake", "max_results": 3})
    response = ChatService(web_search_provider=provider).respond(ChatRequest(message="Quais foram os ultimos governadores do RJ?", include_trace=True))

    assert response.status == "ready"
    assert response.operation_type == "web_search_required"
    assert response.intent["intent_type"] == "public_fact_query"
    assert "Resumo:" in response.message
    assert response.citation_map["sources"]
    assert response.evidence_refs
    assert any(item.stage == "web_provider_called" for item in response.trace)


def test_web_search_disabled_returns_capability_missing_without_private_context_error():
    provider = WebSearchProviderService(config={"enabled": False, "provider_id": "disabled_web", "provider_type": "disabled"})
    response = ChatService(web_search_provider=provider).respond(ChatRequest(message="Qual a versao atual do Kotlin?", include_trace=True))

    assert response.status == "blocked"
    assert response.operation_type == "web_search_required"
    assert response.policy["reason_code"] == "web_search_provider_disabled"
    assert "contexto" not in response.message.casefold()


def test_sandbox_write_file_prompt_creates_real_validated_file():
    target = r"C:\Dev\AIpinho\sandboxes\dopamine_test\resultado.txt"
    import os
    if os.path.exists(target):
        os.remove(target)

    response = ChatService().respond(ChatRequest(message=rf"Crie um arquivo em {target} com o texto: AIpinho funcionou.", include_trace=True))

    assert response.status == "ready"
    assert response.operation_type == "filesystem_write_file"
    assert response.intent["intent_type"] == "filesystem_write_request"
    assert response.policy["workspace_decision"] == "allowed_sandbox"
    assert response.policy["approval_decision"] == "autoapproved_safe_sandbox"
    assert os.path.exists(target)
    assert os.path.getsize(target) > 0
    with open(target, encoding="utf-8") as handle:
        assert "AIpinho funcionou" in handle.read()
    assert any(item.stage == "sandbox_writer_called" for item in response.trace)


def test_sandbox_write_blocks_outside_sandbox():
    response = ChatService().respond(
        ChatRequest(message=r"Crie um arquivo em C:\Windows\resultado.txt com o texto: bloqueado.", include_trace=True)
    )

    assert response.status in {"blocked", "preview"}
    assert response.operation_type in {"filesystem_write_file", "operational_task_request"}
    if response.status == "blocked":
        assert response.policy.get("safe_to_execute") is not True


def test_chat_service_deferred_game_idea_does_not_create_task():
    response = ChatService(model_invocation_service=FakeConversationModelInvocationService()).respond(
        ChatRequest(message="Me dê uma ideia simples de jogo mobile para eu criar depois.", include_trace=True)
    )

    assert response.status == "ok"
    assert response.intent["intent_type"] == "conversation"
    assert response.intent["requires_task"] is False
    assert response.task_id is None
    assert response.preview_id is None


def test_chat_service_reads_sandbox_file_without_web_search():
    target = Path(r"C:\Dev\AIpinho\sandboxes\dopamine_test\resultado.txt")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("Conteudo validado para leitura local.\n", encoding="utf-8")

    response = ChatService().respond(
        ChatRequest(message=rf"Leia o arquivo {target} e confirme o conteúdo.", include_trace=True)
    )

    assert response.status == "ready"
    assert response.operation_type == "filesystem_read_file"
    assert "Conteudo validado" in response.message
    assert response.intent["intent_type"] == "filesystem_read_request"
    assert response.policy["workspace_decision"] == "allowed_sandbox"
    assert response.policy["path"] == str(target)


def test_chat_service_contextual_append_uses_last_sandbox_file():
    target = Path(r"C:\Dev\AIpinho\sandboxes\dopamine_test\contexto.txt")
    if target.exists():
        target.unlink()
    service = ChatService()
    created = service.respond(ChatRequest(message=rf"Crie um arquivo em {target} com o texto: Primeira linha."))
    assert created.status == "ready"

    appended = service.respond(
        ChatRequest(
            session_id=created.session_id,
            message="Adicione uma segunda linha no mesmo arquivo: Segunda linha adicionada.",
            include_trace=True,
        )
    )

    assert appended.status == "ready"
    assert appended.operation_type == "filesystem_append_file"
    assert "Segunda linha adicionada" in target.read_text(encoding="utf-8")


def test_chat_service_blocks_destructive_and_git_write_requests():
    destructive = ChatService().respond(ChatRequest(message=r"Apague recursivamente C:\Dev\AIpinho."))
    git_write = ChatService().respond(ChatRequest(message="Faça git push automaticamente."))

    assert destructive.status == "blocked"
    assert destructive.policy["reason_code"] == "dangerous_operation_blocked"
    assert git_write.status == "blocked"
    assert git_write.policy["reason_code"] == "git_write_blocked"


def test_chat_service_rollback_plan_is_not_patch_rollback_action():
    response = ChatService().respond(
        ChatRequest(
            message=(
                "Prepare um plano de correcao com arquivos candidatos, validation plan "
                "e rollback plan. Nao aplique patch nesta fase."
            )
        )
    )

    assert not any(action.type == "rollback_patch_apply" for action in response.next_actions)
    assert "chat_does_not_rollback_patch" not in response.warnings


def test_chat_service_explicit_patch_rollback_still_requires_endpoint():
    response = ChatService().respond(ChatRequest(message="Execute rollback do patch apply_run_id informado."))

    assert response.status == "preview"
    assert any(action.type == "rollback_patch_apply" for action in response.next_actions)
    assert "chat_does_not_rollback_patch" in response.warnings


def test_chat_service_patch_correction_plan_is_not_patch_apply_action():
    response = ChatService().respond(
        ChatRequest(
            message=(
                "Prepare um plano de correcao minimo com arquivos candidatos. "
                "Nao aplique patch nesta fase."
            )
        )
    )

    assert not any(action.type == "execute_patch_apply" for action in response.next_actions)
    assert "chat_auto_apply_disabled" not in response.warnings


def test_chat_service_explicit_patch_apply_still_blocks_chat_apply():
    response = ChatService().respond(ChatRequest(message="Aplique patch agora para corrigir o projeto."))

    assert response.status == "blocked"
    assert any(action.type == "execute_patch_apply" for action in response.next_actions)
    assert "chat_auto_apply_disabled" in response.warnings


def test_chat_service_idempotent_existing_sandbox_file_is_ready():
    target = Path(r"C:\Dev\AIpinho\sandboxes\dopamine_test\idempotente.txt")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("AIpinho funcionou.\n", encoding="utf-8")

    response = ChatService().respond(
        ChatRequest(message=rf"Crie um arquivo em {target} com o texto: AIpinho funcionou.", include_trace=True)
    )

    assert response.status == "ready"
    assert response.operation_type == "filesystem_write_file"
    assert "idempotent_existing_content" in response.warnings


def test_chat_service_artifact_request_without_source_is_offer_not_degraded():
    response = ChatService().respond(ChatRequest(message="Gere um ZIP com três arquivos txt simples dentro da sandbox."))

    assert response.status in {"ok", "preview"}
    assert response.message_type in {"assistant_final_answer", "artifact_offer"}
    assert response.status != "degraded"
    if response.status == "ok":
        assert response.artifact_links
    else:
        assert "download_link_requires_artifact_id" in response.warnings


def test_chat_service_required_attachment_missing_is_structured_block():
    response = ChatService().respond(ChatRequest(message="Analise com anexo obrigatório e gere um resumo."))

    assert response.status == "blocked"
    assert response.operation_type == "attachment_required_missing"
    assert response.policy["reason_code"] == "attachment_required_missing"


def test_chat_service_sandbox_capability_probe_creates_validated_file():
    response = ChatService().respond(
        ChatRequest(message="Você consegue escrever arquivos na sandbox agora? Teste criando um arquivo pequeno.")
    )

    assert response.status == "ready"
    assert response.operation_type == "filesystem_write_file"
    assert response.policy["workspace_decision"] == "allowed_sandbox"
    assert Path(str(response.policy["path"])).exists()
