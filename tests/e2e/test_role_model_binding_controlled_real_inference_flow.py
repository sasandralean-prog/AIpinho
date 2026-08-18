from aipinho.schemas.roles.role_model_binding import RoleInferenceRequest
from aipinho.services.chat.chat_service import ChatService
from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.services.roles.role_inference_service import RoleInferenceService
from aipinho.services.roles.role_model_gate_service_v2 import RoleModelGateServiceV2


def test_controlled_role_model_flow_never_runs_from_chat_and_preserves_side_effect_boundary():
    chat = ChatService().respond(ChatRequest(message="Rode o modelo da role coder com Qwen 7B agora"))
    assert chat.real_inference is False
    assert chat.status == "preview"

    gate = RoleModelGateServiceV2().decide("coder", RoleInferenceRequest(role_id="coder", prompt="Analise sem ferramentas."))
    assert gate.allowed is True
    assert gate.selected_model_id == "qwen2_5_coder_7b_q4_k_m"

    result = RoleInferenceService().run("coder", RoleInferenceRequest(role_id="coder", prompt="Analise sem ferramentas."))
    assert result.real_inference_attempted is True
    assert result.side_effects is False
    assert result.raw_output_hidden is True
    assert result.status in {"completed", "degraded", "fallback_used", "rejected"}
    if result.real_inference_completed is False:
        assert result.fallback_used is True
