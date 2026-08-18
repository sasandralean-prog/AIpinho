from aipinho.schemas.memory.curated_memory import CuratedMemoryRequest
from tests.unit.curated_memory_test_helpers import candidate_request, memory_stack


def test_memory_approval_curated_persistence_flow_requires_explicit_steps(tmp_path):
    candidate_service, approval_service, curated_store, bridge, persistence = memory_stack(tmp_path)
    candidate = candidate_service.create_candidate(candidate_request("Curated memory needs explicit approval before persistence.")).candidate
    blocked = persistence.persist(CuratedMemoryRequest(candidate_id=candidate.candidate_id, approval_id="approval_missing", operator_confirmed=True))
    assert blocked.status == "blocked"

    approval = bridge.request_approval(candidate.candidate_id)
    still_blocked = persistence.persist(CuratedMemoryRequest(candidate_id=candidate.candidate_id, approval_id=approval.approval_id, operator_confirmed=True))
    assert still_blocked.status == "blocked"

    approval_service.approve(approval.approval_id)
    persisted = persistence.persist(CuratedMemoryRequest(candidate_id=candidate.candidate_id, approval_id=approval.approval_id, operator_confirmed=True))
    assert persisted.status == "active"
    assert curated_store.get_memory(persisted.memory.memory_id).status == "active"
