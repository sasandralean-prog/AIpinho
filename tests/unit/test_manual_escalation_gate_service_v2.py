from aipinho.schemas.roles.role_model_binding import RoleInferenceRequest
from aipinho.services.models.model_registry_service import ModelRegistryService
from aipinho.services.roles.manual_escalation_gate_service import ManualEscalationGateService


def test_manual_escalation_blocks_14b_without_required_acknowledgements():
    model = ModelRegistryService().get_runtime_model("qwen2_5_coder_14b_q5_k_m")
    request = RoleInferenceRequest(role_id="coder", requested_model_id="qwen2_5_coder_14b_q5_k_m", manual_escalation=True)

    decision = ManualEscalationGateService().decide(request, model)

    assert decision["allowed"] is False
    assert decision["status"] == "requires_manual_confirmation"
    assert "operator_confirmation_required" in decision["blocked_reasons"]


def test_manual_escalation_allows_14b_with_reason_and_acknowledgements():
    model = ModelRegistryService().get_runtime_model("qwen2_5_coder_14b_q5_k_m")
    request = RoleInferenceRequest(
        role_id="coder",
        requested_model_id="qwen2_5_coder_14b_q5_k_m",
        manual_escalation=True,
        operator_confirmed=True,
        latency_warning_acknowledged=True,
        reason="Need deeper code review.",
    )

    decision = ManualEscalationGateService().decide(request, model)

    assert decision["allowed"] is True
    assert decision["status"] == "allowed"
    assert "manual_escalation_model_high_latency" in decision["warnings"]
