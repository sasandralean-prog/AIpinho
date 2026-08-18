from aipinho.services.memory.memory_dedupe_resolution_service import MemoryDedupeResolutionService


def test_memory_dedupe_resolution_service_blocks_duplicate_without_resolution():
    result = MemoryDedupeResolutionService().resolve(dedupe_status="duplicate", resolution=None)
    assert result["status"] == "blocked"
    assert result["reason"] == "dedupe_unresolved:duplicate"
