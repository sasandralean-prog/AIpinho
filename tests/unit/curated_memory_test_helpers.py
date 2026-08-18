from __future__ import annotations

from pathlib import Path

from aipinho.schemas.memory.curated_memory import CuratedMemoryRequest
from aipinho.schemas.memory.memory_candidate import MemoryCandidateEvidence, MemoryCandidateRequest, MemoryCandidateScope, MemoryCandidateSource
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.memory.curated_memory_persistence_service import CuratedMemoryPersistenceService
from aipinho.services.memory.curated_memory_store import CuratedMemoryStore
from aipinho.services.memory.memory_approval_bridge import MemoryApprovalBridge
from aipinho.services.memory.memory_candidate_service import MemoryCandidateService
from aipinho.services.memory.memory_candidate_store import MemoryCandidateStore


def candidate_request(text: str = "Quality gate must pass before patch apply.") -> MemoryCandidateRequest:
    return MemoryCandidateRequest(
        text=text,
        kind="policy_decision",
        source=MemoryCandidateSource(source_type="manual_payload", source_id="source-1", source_ref="manual:source-1", trusted=True),
        scope=MemoryCandidateScope(scope_type="policy", reason="unit_test"),
        evidence=[MemoryCandidateEvidence(evidence_id="evidence-1", evidence_type="policy_decision", source_ref="manual:source-1", summary="Policy source")],
    )


def memory_stack(tmp_path: Path):
    candidate_service = MemoryCandidateService(store=MemoryCandidateStore(root=tmp_path / "candidates"))
    approval_service = ApprovalService(store=ApprovalStore(root=tmp_path / "approvals"))
    curated_store = CuratedMemoryStore(root=tmp_path / "curated")
    bridge = MemoryApprovalBridge(candidate_service=candidate_service, approval_service=approval_service)
    persistence = CuratedMemoryPersistenceService(store=curated_store, candidate_service=candidate_service, approval_service=approval_service)
    return candidate_service, approval_service, curated_store, bridge, persistence


def approved_candidate_flow(tmp_path: Path, text: str = "Quality gate must pass before patch apply."):
    candidate_service, approval_service, curated_store, bridge, persistence = memory_stack(tmp_path)
    candidate = candidate_service.create_candidate(candidate_request(text)).candidate
    approval_result = bridge.request_approval(candidate.candidate_id, operator_confirmed=True)
    approval_service.approve(approval_result.approval_id)
    result = persistence.persist(CuratedMemoryRequest(candidate_id=candidate.candidate_id, approval_id=approval_result.approval_id, operator_confirmed=True))
    return candidate, approval_result, result, candidate_service, approval_service, curated_store, bridge, persistence
