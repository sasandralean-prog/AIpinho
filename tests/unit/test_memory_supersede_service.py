from aipinho.schemas.memory.curated_memory import MemorySupersedeRequest
from aipinho.services.memory.memory_supersede_service import MemorySupersedeService
from tests.unit.curated_memory_test_helpers import approved_candidate_flow, candidate_request


def test_memory_supersede_service_marks_memory_superseded(tmp_path):
    _, _, result, candidate_service, approval_service, store, bridge, _ = approved_candidate_flow(tmp_path)
    replacement = candidate_service.create_candidate(candidate_request("Quality gate passed remains required before patch apply.")).candidate
    approval = bridge.request_approval(replacement.candidate_id)
    approval_service.approve(approval.approval_id)
    updated = MemorySupersedeService(store=store, candidate_service=candidate_service, approval_service=approval_service).supersede(
        result.memory.memory_id,
        MemorySupersedeRequest(candidate_id=replacement.candidate_id, approval_id=approval.approval_id, operator_confirmed=True, reason="newer rule"),
    )
    assert updated.status == "active"
    assert store.get_memory(result.memory.memory_id).status == "superseded"
