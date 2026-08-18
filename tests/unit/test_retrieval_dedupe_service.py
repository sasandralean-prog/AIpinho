from aipinho.services.rag.retrieval_dedupe_service import RetrievalDedupeService
from tests.unit.retrieval_test_helpers import cited_hit


def test_retrieval_dedupe_prefers_higher_score():
    low = cited_hit("same excerpt", 1)
    high = cited_hit("same excerpt", 5)
    result = RetrievalDedupeService().dedupe([low, high])
    assert len(result) == 1
    assert result[0].score == 5
