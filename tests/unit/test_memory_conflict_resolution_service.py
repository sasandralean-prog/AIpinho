from aipinho.services.memory.memory_conflict_resolution_service import MemoryConflictResolutionService


def test_memory_conflict_resolution_service_requires_explicit_resolution():
    result = MemoryConflictResolutionService().resolve(has_conflict=True, resolution=None)
    assert result["status"] == "blocked"
    assert result["reason"] == "unresolved_conflict"
