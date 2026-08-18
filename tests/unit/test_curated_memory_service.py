from aipinho.schemas.memory.curated_memory import CuratedMemoryRequest
from aipinho.services.memory.curated_memory_service import CuratedMemoryService
from tests.unit.curated_memory_test_helpers import candidate_request, memory_stack


def test_curated_memory_service_persists_with_injected_dependencies(tmp_path):
    candidate_service, approval_service, curated_store, bridge, _ = memory_stack(tmp_path)
    candidate = candidate_service.create_candidate(candidate_request()).candidate
    approval = bridge.request_approval(candidate.candidate_id)
    approval_service.approve(approval.approval_id)
    service = CuratedMemoryService(store=curated_store, candidate_service=candidate_service, approval_service=approval_service)
    result = service.persist_from_candidate(CuratedMemoryRequest(candidate_id=candidate.candidate_id, approval_id=approval.approval_id, operator_confirmed=True))
    assert result.status == "active"
    assert service.get_memory(result.memory.memory_id).memory_id == result.memory.memory_id
    assert service.status()["auto_prompt_memory_enabled"] is False
