from aipinho.schemas.memory.curated_memory import CuratedMemoryRequest
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.memory.curated_memory_persistence_service import CuratedMemoryPersistenceService
from aipinho.services.memory.memory_approval_bridge import MemoryApprovalBridge
from aipinho.services.memory.memory_candidate_service import MemoryCandidateService
from aipinho.services.memory.memory_candidate_store import MemoryCandidateStore
from tests.unit.curated_memory_test_helpers import approved_candidate_flow, candidate_request, memory_stack


def test_curated_memory_persistence_requires_candidate_approval_and_operator_confirmation(tmp_path):
    candidate, approval_result, result, *_ = approved_candidate_flow(tmp_path)
    assert result.status == "active"
    assert result.memory.source.candidate_id == candidate.candidate_id
    assert result.memory.source.approval_id == approval_result.approval_id


def test_curated_memory_persistence_blocks_duplicate_active_memory(tmp_path):
    candidate_service, approval_service, curated_store, bridge, persistence = memory_stack(tmp_path)
    first = candidate_service.create_candidate(candidate_request("Memory approvals require evidence.")).candidate
    first_approval = bridge.request_approval(first.candidate_id)
    approval_service.approve(first_approval.approval_id)
    assert persistence.persist(CuratedMemoryRequest(candidate_id=first.candidate_id, approval_id=first_approval.approval_id, operator_confirmed=True)).status == "active"
    second_candidate_service = MemoryCandidateService(store=MemoryCandidateStore(root=tmp_path / "second_candidates"))
    second_approval_service = ApprovalService(store=ApprovalStore(root=tmp_path / "second_approvals"))
    second_bridge = MemoryApprovalBridge(candidate_service=second_candidate_service, approval_service=second_approval_service)
    second_persistence = CuratedMemoryPersistenceService(store=curated_store, candidate_service=second_candidate_service, approval_service=second_approval_service)
    second = second_candidate_service.create_candidate(candidate_request("Memory approvals require evidence.")).candidate
    second_approval = second_bridge.request_approval(second.candidate_id)
    second_approval_service.approve(second_approval.approval_id)
    blocked = second_persistence.persist(CuratedMemoryRequest(candidate_id=second.candidate_id, approval_id=second_approval.approval_id, operator_confirmed=True))
    assert blocked.status == "blocked"
