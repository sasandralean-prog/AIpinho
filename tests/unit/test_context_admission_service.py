from aipinho.schemas.rag.integration.contracts import ContextAdmissionRequest
from aipinho.services.rag.integration.context_admission_service import ContextAdmissionService
from tests.unit.rag_memory_test_helpers import cited_retrieval, explicit_policy, memory


def admit(**kwargs):
    return ContextAdmissionService().admit(ContextAdmissionRequest(**kwargs))


def test_valid_retrieval_bundle_is_admitted():
    result, bundle = cited_retrieval()
    decision = admit(policy_decision=explicit_policy(), retrieval_result=result, retrieval_context_bundle=bundle)
    assert decision.safe_for_prompt_assembly is True
    assert decision.citation_map.valid is True


def test_uncited_retrieval_item_is_blocked():
    result, bundle = cited_retrieval()
    bundle["hits"][0]["citation"] = None
    decision = admit(policy_decision=explicit_policy(), retrieval_result=result, retrieval_context_bundle=bundle)
    assert decision.status == "blocked"
    assert "retrieval_contains_uncited_hits" in decision.blocked_reasons


def test_active_memory_is_admitted_but_candidate_and_expired_are_blocked():
    policy = explicit_policy(sources=["curated_memory"])
    active = admit(policy_decision=policy, memory_items=[memory()])
    candidate = admit(policy_decision=policy, memory_items=[memory(status="candidate")])
    expired = admit(policy_decision=policy, memory_items=[memory(status="expired")])
    assert active.safe_for_prompt_assembly is True
    assert candidate.status == "blocked"
    assert expired.status == "blocked"


def test_sensitive_context_is_blocked():
    result, bundle = cited_retrieval(text="password=supersecret")
    decision = admit(policy_decision=explicit_policy(), retrieval_result=result, retrieval_context_bundle=bundle)
    assert decision.status == "blocked"
    assert "sensitive_context_blocked" in decision.blocked_reasons


def test_over_budget_returns_partial_with_warnings():
    result, bundle = cited_retrieval(text="x" * 4000)
    decision = admit(policy_decision=explicit_policy(), retrieval_result=result, retrieval_context_bundle=bundle, budget={"max_context_chars_total": 100, "max_context_chars_per_item": 80})
    assert decision.status == "partial"
    assert "context_items_truncated_by_budget" in decision.warnings

