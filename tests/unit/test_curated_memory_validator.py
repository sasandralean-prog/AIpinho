from aipinho.schemas.memory.memory_candidate import MemoryCandidateRequest
from aipinho.services.memory.curated_memory_validator import CuratedMemoryValidator
from aipinho.services.memory.memory_candidate_service import MemoryCandidateService
from aipinho.services.memory.memory_candidate_store import MemoryCandidateStore
from tests.unit.curated_memory_test_helpers import candidate_request


def test_curated_memory_validator_requires_candidate_source_scope_and_evidence(tmp_path):
    service = MemoryCandidateService(store=MemoryCandidateStore(root=tmp_path))
    request = MemoryCandidateRequest(text="Technical rule.", kind="policy_decision")
    candidate = service.create_candidate(request).candidate
    validation = CuratedMemoryValidator().validate_candidate(candidate)
    assert not validation.allowed
    assert "source_missing" in validation.blocked_reasons


def test_curated_memory_validator_accepts_valid_candidate(tmp_path):
    service = MemoryCandidateService(store=MemoryCandidateStore(root=tmp_path))
    candidate = service.create_candidate(candidate_request()).candidate
    validation = CuratedMemoryValidator().validate_candidate(candidate)
    assert validation.allowed
