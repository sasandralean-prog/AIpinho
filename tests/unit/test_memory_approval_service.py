from aipinho.services.memory.memory_approval_service import MemoryApprovalService
from tests.unit.curated_memory_test_helpers import candidate_request, memory_stack


def test_memory_approval_service_reports_status_and_requests_from_candidate(tmp_path):
    candidate_service, approval_service, _, _, _ = memory_stack(tmp_path)
    candidate = candidate_service.create_candidate(candidate_request()).candidate
    service = MemoryApprovalService(candidate_service=candidate_service, approval_service=approval_service)
    result = service.request_from_candidate(candidate.candidate_id)
    assert result.status == "pending"
    assert service.status()["approval_required"] is True
