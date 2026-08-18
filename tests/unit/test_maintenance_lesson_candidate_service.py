import inspect
from aipinho.services.maintenance.maintenance_lesson_candidate_service import MaintenanceLessonCandidateService

def test_lesson_candidate_does_not_mutate_curated_memory():
    source = inspect.getsource(MaintenanceLessonCandidateService)
    assert "memory_mutation_performed=False" in source
    assert "MemoryApprovalService" not in source
    assert "memory_service" not in source
