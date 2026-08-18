from aipinho.schemas.memory.memory_candidate import MemoryCandidateScope
from aipinho.services.memory.memory_candidate_dedupe_service import MemoryCandidateDedupeService
from aipinho.services.memory.memory_candidate_service import MemoryCandidateService
from aipinho.services.memory.memory_candidate_store import MemoryCandidateStore
from tests.unit.test_memory_candidate_service import valid_request


def test_dedupe_exact_and_unique(tmp_path):
    svc = MemoryCandidateService(MemoryCandidateStore(tmp_path))
    existing = [svc.create_candidate(valid_request()).candidate]
    service = MemoryCandidateDedupeService()
    exact = service.evaluate("Patch apply requires quality gate passed.", kind="policy_decision", scope=MemoryCandidateScope(scope_type="policy"), existing=existing)
    unique = service.evaluate("A completely different operational procedure.", kind="operational_procedure", scope=MemoryCandidateScope(scope_type="runtime"), existing=existing)
    assert exact.status == "duplicate"
    assert unique.status == "unique"
