from aipinho.schemas.roles.role_model_binding import RoleInferenceRequest
from aipinho.services.roles.role_model_gate_service_v2 import RoleModelGateServiceV2


def test_coder_role_uses_qwen_coder_7b_by_default():
    decision = RoleModelGateServiceV2().decide("coder", RoleInferenceRequest(role_id="coder", prompt="Revise este trecho."))

    assert decision.allowed is True
    assert decision.status in {"allowed", "degraded"}
    assert decision.selected_model_id == "qwen2_5_coder_7b_q4_k_m"
    assert decision.provider_id == "llama_cpp_text"
    assert decision.fallback_model_id == "qwen2_5_coder_1_5b_q8_0"


def test_14b_model_cannot_be_auto_selected_without_manual_escalation():
    request = RoleInferenceRequest(role_id="coder", requested_model_id="qwen2_5_coder_14b_q5_k_m")

    decision = RoleModelGateServiceV2().decide("coder", request)

    assert decision.allowed is False
    assert decision.status in {"blocked", "requires_manual_confirmation"}
    assert "manual_only_model_cannot_be_auto_selected" in decision.blocked_reasons


def test_manual_14b_requires_all_operator_confirmations():
    request = RoleInferenceRequest(role_id="coder", requested_model_id="qwen2_5_coder_14b_q5_k_m", manual_escalation=True)

    decision = RoleModelGateServiceV2().decide("coder", request, model_id="qwen2_5_coder_14b_q5_k_m", manual=True)

    assert decision.allowed is False
    assert decision.status == "requires_manual_confirmation"
    assert "operator_confirmation_required" in decision.blocked_reasons
    assert "latency_warning_acknowledgement_required" in decision.blocked_reasons
    assert "manual_escalation_reason_required" in decision.blocked_reasons


def test_enabled_vision_role_still_respects_provider_runtime_gate():
    decision = RoleModelGateServiceV2().decide("vision_analyst", RoleInferenceRequest(role_id="vision_analyst"))

    assert decision.allowed is False
    assert decision.selected_model_id == "qwen2_5_vl_7b_q4_k_m"
    assert "provider_runtime_not_text_inference" in decision.blocked_reasons
