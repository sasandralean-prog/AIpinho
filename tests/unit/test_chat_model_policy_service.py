from types import SimpleNamespace

from aipinho.schemas.chat.manual_chat_inference_request import ManualChatInferenceRequest
from aipinho.services.chat.chat_model_policy_service import ChatModelPolicyService


class FakeProfileService:
    def get_profile(self, profile_id):
        return SimpleNamespace(
            profile_id=profile_id,
            enabled=True,
            manual_only=True,
            allow_chat_auto_use=False,
            allow_report_auto_use=False,
            allow_analysis_auto_use=False,
            prompt_id=None,
            output_contract_type="chat_response",
            safety_envelope_id="local_manual_inference",
        )


class FakeManualGate:
    def decide(self, request, profile=None):
        return SimpleNamespace(
            allowed=True,
            warnings=[],
            blocked_reasons=[],
            model_dump=lambda: {"allowed": True, "status": "allowed", "blocked_reasons": []},
        )


def _enabled_service():
    return ChatModelPolicyService(
        config={
            "normal_chat": {"real_inference_enabled": False, "default_model_id": "stub.default"},
            "manual_chat": {"enabled": True, "require_request_opt_in": True, "require_operator_confirmation": True, "require_profile_enabled": True},
            "allowed_profiles": ["p"],
            "blocked_capabilities": {"tool_calling": True, "write_files": True},
        },
        manual_policy={"manual_inference": {"enabled": True}},
        profile_service=FakeProfileService(),
        manual_gate=FakeManualGate(),
    )


def test_chat_model_policy_default_disables_manual_inference():
    status = ChatModelPolicyService().status()
    assert status["normal_chat_real_inference"] is True
    assert status["manual_chat_inference_enabled"] is False
    assert status["default_model"] == "qwen3_1_7b_q6_k"


def test_chat_model_policy_requires_opt_in_and_confirmation():
    result = _enabled_service().validate_request(ManualChatInferenceRequest(message="Ola", profile_id="p"))
    assert result["allowed"] is False
    assert "request_opt_in_missing" in result["blocked_reasons"]
    assert "operator_confirmation_missing" in result["blocked_reasons"]


def test_chat_model_policy_allows_when_manual_contract_satisfied():
    result = _enabled_service().validate_request(ManualChatInferenceRequest(message="Ola", profile_id="p", allow_real_inference=True, operator_confirmed=True))
    assert result["allowed"] is True
