from aipinho.schemas.rag.retrieval_request import RetrievalBudget
from aipinho.services.rag.retrieval_query_service import RetrievalQueryService


def test_retrieval_query_normalizes_tokenizes_and_limits():
    service = RetrievalQueryService()
    query = service.normalize("  Validation   Gate  ", RetrievalBudget(max_query_chars=20))
    assert query.normalized == "validation gate"
    assert query.tokens == ["validation", "gate"]


def test_retrieval_query_rejects_empty():
    service = RetrievalQueryService()
    assert service.validate(service.normalize("")).valid is False
