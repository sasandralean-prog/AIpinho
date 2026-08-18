from aipinho.schemas.memory.curated_memory import MemorySearchRequest
from aipinho.services.memory.curated_memory_search_service import CuratedMemorySearchService
from tests.unit.curated_memory_test_helpers import approved_candidate_flow


def test_curated_memory_search_filters_active_memory(tmp_path):
    _, _, result, _, _, store, *_ = approved_candidate_flow(tmp_path, "Memory search must only return curated memories.")
    search = CuratedMemorySearchService(store=store).search(MemorySearchRequest(text="curated", status="active"))
    assert len(search.results) == 1
    assert search.results[0].memory_id == result.memory.memory_id
