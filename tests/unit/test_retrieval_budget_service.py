from aipinho.schemas.rag.retrieval_request import RetrievalBudget
from aipinho.services.rag.retrieval_budget_service import RetrievalBudgetService
from tests.unit.retrieval_test_helpers import cited_hit


def test_retrieval_budget_limits_hits_and_context_chars():
    hits = [cited_hit(f"hit {index}") for index in range(5)]
    output, warnings, status = RetrievalBudgetService().apply(hits, RetrievalBudget(max_hits_total=2, max_context_chars=100))
    assert len(output) == 2
    assert status == "partial"
    assert "hit_budget_truncated" in warnings
