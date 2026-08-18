from aipinho.services.evaluation.fallback_policy_service import FallbackPolicyService


def test_fallback_policy_chat_uses_deterministic_speaker():
    decision = FallbackPolicyService().decide(purpose="chat", status="rejected", violations=["invalid_json"])
    assert decision.should_fallback is True
    assert decision.fallback_type == "deterministic_speaker"


def test_fallback_policy_report_uses_deterministic_report():
    decision = FallbackPolicyService().decide(purpose="project_report", status="rejected", violations=["missing_evidence"])
    assert decision.fallback_type == "deterministic_report"


def test_fallback_policy_task_preview_uses_policy_preview():
    decision = FallbackPolicyService().decide(purpose="task_preview", status="rejected", violations=["invalid_json"])
    assert decision.fallback_type == "policy_preview"


def test_fallback_policy_never_falls_back_to_unvalidated_real_model():
    decision = FallbackPolicyService().decide(purpose="chat", status="rejected", violations=["invalid_json"], real_inference=True)
    assert decision.fallback_type == "safe_error"
