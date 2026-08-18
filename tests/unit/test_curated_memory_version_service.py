from aipinho.services.memory.curated_memory_version_service import CuratedMemoryVersionService
from tests.unit.curated_memory_test_helpers import approved_candidate_flow


def test_curated_memory_version_service_creates_initial_version(tmp_path):
    _, _, result, *_ = approved_candidate_flow(tmp_path)
    version = CuratedMemoryVersionService().initial_version(result.memory)
    assert version.version == 1
    assert version.memory_id == result.memory.memory_id
