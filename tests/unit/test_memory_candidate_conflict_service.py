from aipinho.schemas.memory.memory_candidate import MemoryCandidateScope
from aipinho.services.memory.memory_candidate_conflict_service import MemoryCandidateConflictService
from aipinho.services.memory.memory_candidate_service import MemoryCandidateService
from aipinho.services.memory.memory_candidate_store import MemoryCandidateStore
from tests.unit.test_memory_candidate_service import valid_request


def test_conflict_enabled_disabled(tmp_path):
    svc = MemoryCandidateService(MemoryCandidateStore(tmp_path))
    existing = [svc.create_candidate(valid_request("Feature enabled for the policy.")).candidate]
    conflict = MemoryCandidateConflictService().evaluate("Feature disabled for the policy.", kind="policy_decision", scope=MemoryCandidateScope(scope_type="policy"), existing=existing)
    assert conflict.has_conflict
