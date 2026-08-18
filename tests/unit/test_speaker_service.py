from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.intent.prompt_analysis_request import PromptAnalysisRequest
from aipinho.services.policy_kernel.policy_kernel_service import PolicyKernelService
from aipinho.services.prompt_intelligence.prompt_intelligence_service import PromptIntelligenceService
from aipinho.services.speaker.speaker_service import SpeakerService


def _parts(prompt: str):
    pi = PromptIntelligenceService()
    analysis = pi.analyze(PromptAnalysisRequest(prompt=prompt))
    policy_request = pi.to_policy_request(analysis.intent_map)
    decision = PolicyKernelService().resolve(policy_request)
    preview = PolicyKernelService().contract_preview(policy_request)
    preview_dict = preview.model_dump() if hasattr(preview, "model_dump") else preview.dict()
    return ChatRequest(message=prompt), analysis.intent_map, decision, preview_dict


def test_speaker_conversation_response():
    request, intent_map, decision, preview = _parts("Bom dia, tudo certo?")
    message = SpeakerService().compose_response(request=request, intent_map=intent_map, policy_decision=decision, contract_preview=preview, status="ok")
    assert "execut" not in message.lower() or "nao" in message.lower()


def test_speaker_self_analysis_response_is_grounded():
    request, intent_map, decision, preview = _parts("Explique sua arquitetura atual")
    message = SpeakerService().compose_response(request=request, intent_map=intent_map, policy_decision=decision, contract_preview=preview, status="ok")
    assert "AIpinho" in message
    assert "Fontes usadas" in message


def test_speaker_capability_response_lists_limits():
    request, intent_map, decision, preview = _parts("O que voce consegue fazer?")
    message = SpeakerService().compose_response(request=request, intent_map=intent_map, policy_decision=decision, contract_preview=preview, status="ok")
    assert "Hoje eu consigo" in message
    assert "Ainda nao consigo" in message


def test_speaker_blocked_response():
    request, intent_map, decision, preview = _parts(r"Corrija C:\PinhoabacaxiAI")
    message = SpeakerService().compose_response(request=request, intent_map=intent_map, policy_decision=decision, contract_preview=preview, status="blocked")
    assert "bloqueado" in message.lower()


def test_speaker_clarification_response():
    request, intent_map, decision, preview = _parts("Arrume tudo")
    message = SpeakerService().compose_response(request=request, intent_map=intent_map, policy_decision=decision, contract_preview=preview, status="needs_clarification")
    assert "esclarecimento" in message


def test_speaker_preview_response():
    request, intent_map, decision, preview = _parts(r"Conserte o bug no projeto C:\Dev\AIpinho")
    message = SpeakerService().compose_response(request=request, intent_map=intent_map, policy_decision=decision, contract_preview=preview, status="preview")
    assert "preview" in message.lower()
    assert "nenhuma" in message.lower()
