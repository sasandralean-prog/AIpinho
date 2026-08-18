from aipinho.services.memory.memory_candidate_status_service import MemoryCandidateStatusService


def test_approved_transition_blocked():
    service = MemoryCandidateStatusService()
    assert service.can_transition("candidate", "approved") is False
    assert service.can_transition("candidate", "rejected") is True
