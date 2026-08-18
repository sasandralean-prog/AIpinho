from aipinho.services.memory.curated_memory_search_service import CuratedMemorySearchService
from aipinho.services.rag.sources.curated_memory_retrieval_source import CuratedMemoryRetrievalSource
from tests.unit.curated_memory_test_helpers import approved_candidate_flow
from tests.unit.retrieval_test_helpers import request


def test_curated_memory_retrieval_requires_explicit_and_returns_memory_citation(tmp_path):
    _, _, result, _, _, store, *_ = approved_candidate_flow(tmp_path, "Patch apply requires validation gate.")
    source = CuratedMemoryRetrievalSource(search=CuratedMemorySearchService(store=store))
    assert source.retrieve(request(query="validation", sources=["curated_memory"], explicit=False)) == []
    hits = source.retrieve(request(query="validation", sources=["curated_memory"], explicit=True))
    assert hits
    assert hits[0].citation.citation_type == "memory_id"
    assert hits[0].metadata["memory_id"] == result.memory.memory_id
