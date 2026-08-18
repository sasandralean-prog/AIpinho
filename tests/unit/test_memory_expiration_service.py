from aipinho.services.memory.memory_expiration_service import MemoryExpirationService
from tests.unit.curated_memory_test_helpers import approved_candidate_flow


def test_memory_expiration_service_marks_memory_expired(tmp_path):
    _, _, result, _, _, store, *_ = approved_candidate_flow(tmp_path)
    updated = MemoryExpirationService(store=store).expire(result.memory.memory_id, "outdated")
    assert updated.status == "expired"
