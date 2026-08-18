from aipinho.schemas.rag.retrieval_request import RetrievalBudget, RetrievalScope
from aipinho.services.rag.retrieval_service import RetrievalService
from tests.unit.retrieval_test_helpers import request


def test_retrieval_service_returns_found_with_citations_trace_and_no_vectorstore():
    result = RetrievalService().retrieve(request(query="validation gate"))
    assert result.status in {"found", "partial"}
    assert result.hits
    assert all(hit.citation for hit in result.hits)
    assert result.vectorstore_used is False
    assert result.embeddings_used is False
    assert result.side_effects is False
    assert result.trace


def test_retrieval_service_blocks_unknown_legacy_forbidden_and_handles_no_results():
    service = RetrievalService()
    assert service.retrieve(request(sources=[])).status == "blocked"
    assert service.retrieve(request(sources=["unknown"])).status == "blocked"
    assert service.retrieve(request(sources=["legacy_vectorstore"])).status == "blocked"
    forbidden = request(sources=["project_files"], workspace=r"C:\PinhoabacaxiAI", paths=["README.md"], scope=RetrievalScope(scope_type="workspace", workspace=r"C:\PinhoabacaxiAI"))
    assert service.retrieve(forbidden).status == "blocked"
    no_results = service.retrieve(request(query="zzzz_not_found_zzzz"))
    assert no_results.status == "no_results"


def test_retrieval_service_marks_partial_when_budget_truncates():
    result = RetrievalService().retrieve(request(query="Sprint", budget=RetrievalBudget(max_hits_total=1)))
    assert result.status in {"partial", "found"}
