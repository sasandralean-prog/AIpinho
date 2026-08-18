from aipinho.services.chat.chat_response_policy_service import ChatResponsePolicyService


def test_chat_response_policy_loads_required_defaults():
    policy = ChatResponsePolicyService().load()
    status = policy.status()
    assert status["status"] == "ok"
    assert policy.max_message_chars() == 4000
    assert policy.raw_debug_in_chat() is False


def test_chat_response_policy_has_required_response_types():
    policy = ChatResponsePolicyService().load()
    for key in [
        "conversation",
        "self_analysis",
        "capability_explanation",
        "in_chat_final_report",
        "readonly_analysis",
        "artifact_generation",
        "patch_request",
        "ambiguity",
        "blocked",
    ]:
        assert policy.response_for(key)