from aipinho.services.rag.integration.retrieval_context_selector import RetrievalContextSelector
from tests.unit.rag_memory_test_helpers import cited_retrieval


def test_safe_retrieval_bundle_selected():
    result, bundle = cited_retrieval()
    selection = RetrievalContextSelector().select(result, bundle, usage_mode="explicit_user_request")
    assert len(selection.items) == 1
    assert not selection.blocked_reasons


def test_blocked_retrieval_status_blocks():
    result, bundle = cited_retrieval(status="blocked")
    selection = RetrievalContextSelector().select(result, bundle, usage_mode="explicit_user_request")
    assert any("retrieval_status_not_admissible" in reason for reason in selection.blocked_reasons)


def test_uncited_hit_blocks():
    result, bundle = cited_retrieval()
    bundle["hits"][0]["citation"] = None
    selection = RetrievalContextSelector().select(result, bundle, usage_mode="explicit_user_request")
    assert "retrieval_contains_uncited_hits" in selection.blocked_reasons


def test_partial_result_carries_warnings():
    result, bundle = cited_retrieval(status="partial")
    selection = RetrievalContextSelector().select(result, bundle, usage_mode="explicit_user_request")
    assert "partial_source" in selection.warnings

