from aipinho.schemas.memory.memory_candidate import MemoryCandidateRequest, MemoryCandidateScope
from aipinho.services.memory.memory_candidate_service import MemoryCandidateService
from aipinho.services.memory.memory_candidate_store import MemoryCandidateStore
from tests.unit.test_memory_candidate_service import valid_request


def test_raw_log_blocks(tmp_path):
    req = valid_request("Traceback (most recent call last)\nraw log\n" * 3)
    result = MemoryCandidateService(MemoryCandidateStore(tmp_path)).create_candidate(req)
    assert result.candidate.status == "blocked"


def test_full_file_content_blocks(tmp_path):
    req = valid_request("\n".join(f"line {i}" for i in range(100)))
    result = MemoryCandidateService(MemoryCandidateStore(tmp_path)).create_candidate(req)
    assert result.candidate.status == "blocked"


def test_missing_scope_blocks(tmp_path):
    req = valid_request()
    req.scope = MemoryCandidateScope(scope_type="")
    result = MemoryCandidateService(MemoryCandidateStore(tmp_path)).create_candidate(req)
    assert "scope_missing" in result.candidate.blocked_reasons
