from aipinho.services.roles.role_model_binding_service import RoleModelBindingService
from aipinho.services.roles.role_model_fallback_service import RoleModelFallbackService


def test_role_model_fallback_uses_configured_safe_fallback():
    binding = RoleModelBindingService().get_binding("coder")
    assert binding is not None

    decision = RoleModelFallbackService().decide(binding, reason="primary_blocked")

    assert decision.fallback_allowed is True
    assert decision.fallback_model_id == "qwen2_5_coder_1_5b_q8_0"


def test_deterministic_fallback_never_claims_tools_or_side_effects():
    response = RoleModelFallbackService().deterministic_response(
        request_id="req_test",
        role_id="coder",
        fallback_model_id="qwen2_5_coder_1_5b_q8_0",
        reason="provider_blocked",
    )

    assert response.status == "completed"
    assert response.real_inference is False
    assert "No tools, files, patch, shell, git or network were used." in response.content
