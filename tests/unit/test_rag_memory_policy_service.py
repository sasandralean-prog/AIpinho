from aipinho.schemas.rag.integration.contracts import RAGMemoryPolicyRequest
from aipinho.services.rag.integration.rag_memory_policy_service import RAGMemoryPolicyService


def decide(**overrides):
    payload = {
        "usage_mode": "explicit_user_request",
        "intent_type": "readonly_analysis",
        "requested_sources": ["project_reports", "curated_memory"],
        "allow_retrieval": True,
        "allow_curated_memory": True,
        "user_request": "Use governed context.",
    }
    payload.update(overrides)
    return RAGMemoryPolicyService().decide(RAGMemoryPolicyRequest(**payload))


def test_explicit_retrieval_and_memory_allowed():
    result = decide()
    assert result.allowed is True
    assert result.requires_context_admission is True
    assert {"project_reports", "curated_memory"}.issubset(set(result.allowed_sources))


def test_automatic_chat_and_prompt_injection_are_blocked():
    chat = decide(usage_mode="automatic_chat")
    prompt = decide(usage_mode="automatic_prompt_assembly")
    assert chat.allowed is False
    assert prompt.allowed is False


def test_curated_memory_requires_explicit_mode_and_flag():
    result = decide(usage_mode="role_pipeline_allowed", allow_curated_memory=True, requested_sources=["curated_memory"])
    assert result.allowed is False
    assert any("curated_memory_explicit_required" in reason for reason in result.blocked_reasons)


def test_unknown_source_is_blocked():
    result = decide(requested_sources=["unknown_source"], allow_curated_memory=False)
    assert result.allowed is False
    assert any("unregistered_source" in reason for reason in result.blocked_reasons)

