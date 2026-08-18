from aipinho.schemas.memory.memory_candidate import MemoryCandidateScope
from aipinho.services.memory.memory_candidate_scope_service import MemoryCandidateScopeService


def test_scope_forbidden_root_blocks():
    reasons = MemoryCandidateScopeService().validate(MemoryCandidateScope(scope_type="workspace", workspace="C:\\PinhoabacaxiAI\\x"))
    assert "forbidden_root_scope" in reasons


def test_scope_missing_blocks():
    assert "scope_missing" in MemoryCandidateScopeService().validate(MemoryCandidateScope(scope_type=""))
