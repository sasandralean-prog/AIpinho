from aipinho.services.rag.retrieval_query_service import RetrievalQueryService
from aipinho.services.rag.retrieval_ranker import RetrievalRanker
from tests.unit.retrieval_test_helpers import cited_hit


def test_retrieval_ranker_is_deterministic_and_prefers_exact_phrase():
    hits = [cited_hit("Evidence exists.", 0), cited_hit("Validation gate requires evidence.", 0)]
    query = RetrievalQueryService().normalize("validation gate")
    first = RetrievalRanker().rank(hits, query)
    second = RetrievalRanker().rank(hits, query)
    assert [item.excerpt for item in first] == [item.excerpt for item in second]
    assert first[0].excerpt.startswith("Validation gate")
