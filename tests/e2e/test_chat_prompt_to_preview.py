from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.services.chat.chat_service import ChatService


def _chat(message: str, *, preview: bool = False):
    mode = "preview" if preview else "normal"
    return ChatService().respond(ChatRequest(message=message, mode=mode, include_trace=preview))


def test_greeting_case():
    response = _chat("Bom dia, tudo certo?")
    assert response.status == "ok"
    assert response.intent["intent_type"] == "conversation"
    assert response.intent["requires_task"] is False
    assert response.intent["workspace"]["declared"] is False


def test_self_analysis_case():
    response = _chat("Explique sua arquitetura atual")
    assert response.status == "ok"
    assert response.intent["intent_type"] == "self_analysis"
    assert response.intent["requires_workspace"] is False
    assert "AIpinho esta no estagio:" in response.message
    assert "Fontes usadas:" in response.message


def test_capability_case():
    response = _chat("O que voce consegue fazer?")
    assert response.status == "ok"
    assert response.intent["intent_type"] == "capability_explanation"
    assert response.intent["requires_task"] is False
    assert "Ainda nao consigo" in response.message


def test_chat_report_case():
    response = _chat("Faca um report final desta conversa")
    assert response.status == "ok"
    assert response.intent["intent_type"] == "in_chat_final_report"
    assert response.intent["output_channel"] == "chat"
    assert response.intent["requires_task"] is False


def test_artifact_report_case():
    response = _chat("Salve um relatorio em reports/final.md")
    assert response.status in {"preview", "needs_clarification"}
    assert response.intent["intent_type"] == "artifact_generation"
    assert "write_files" in response.policy["approval_required_for"]
    assert response.policy["safe_to_execute"] is False


def test_readonly_project_analysis_case():
    response = _chat(r"Explique a arquitetura do projeto C:\Dev\AIpinho sem alterar nada")
    assert response.status == "preview"
    assert response.intent["intent_type"] == "readonly_analysis"
    assert response.policy["safe_to_execute"] is True
    assert response.contract_preview


def test_patch_request_case():
    response = _chat(r"Conserte o bug no projeto C:\Dev\AIpinho")
    assert response.status == "preview"
    assert response.intent["intent_type"] == "patch_request"
    assert "apply_patch" in response.contract_preview["requested_actions"]
    assert response.policy["safe_to_execute"] is False


def test_ambiguity_case():
    response = _chat("Arrume tudo")
    assert response.status == "needs_clarification"
    assert response.intent["requires_clarification"] is True
    assert response.actions == ["clarify_request"]


def test_forbidden_root_case():
    response = _chat(r"Corrija C:\Windows")
    assert response.status == "blocked"
    assert response.intent["workspace"]["protected"] is True
    assert response.policy["safe_to_execute"] is False


def test_theoretical_question_case():
    response = _chat("Como consertar arquitetura em teoria?")
    assert response.status == "ok"
    assert response.intent["intent_type"] == "conversation"
    assert response.intent["requires_task"] is False
    assert response.policy["safe_to_execute"] is False
