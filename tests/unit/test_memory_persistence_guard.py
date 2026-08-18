from aipinho.schemas.memory.curated_memory import CuratedMemoryRequest
from tests.unit.curated_memory_test_helpers import memory_stack, candidate_request


def test_memory_persistence_guard_blocks_without_approved_approval(tmp_path):
    candidate_service, _, _, bridge, persistence = memory_stack(tmp_path)
    candidate = candidate_service.create_candidate(candidate_request()).candidate
    approval_result = bridge.request_approval(candidate.candidate_id)
    result = persistence.persist(CuratedMemoryRequest(candidate_id=candidate.candidate_id, approval_id=approval_result.approval_id, operator_confirmed=True))
    assert result.status == "blocked"
    assert any(reason.startswith("approval_not_approved") for reason in result.blocked_reasons)


def test_memory_persistence_guard_blocks_without_operator_confirmation(tmp_path):
    candidate, approval_result, _, _, _, _, persistence = approved_candidate_seed(tmp_path)
    result = persistence.persist(CuratedMemoryRequest(candidate_id=candidate.candidate_id, approval_id=approval_result.approval_id, operator_confirmed=False))
    assert result.status == "blocked"
    assert "operator_confirmation_required" in result.blocked_reasons


def approved_candidate_seed(tmp_path):
    candidate_service, approval_service, curated_store, bridge, persistence = memory_stack(tmp_path)
    candidate = candidate_service.create_candidate(candidate_request()).candidate
    approval_result = bridge.request_approval(candidate.candidate_id)
    approval_service.approve(approval_result.approval_id)
    return candidate, approval_result, curated_store, candidate_service, approval_service, bridge, persistence
