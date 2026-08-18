from __future__ import annotations

from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.memory.memory_approval_bridge import MemoryApprovalBridge
from aipinho.services.memory.memory_candidate_service import MemoryCandidateService


class MemoryApprovalService:
    def __init__(
        self,
        candidate_service: MemoryCandidateService | None = None,
        approval_service: ApprovalService | None = None,
        bridge: MemoryApprovalBridge | None = None,
    ) -> None:
        self.bridge = bridge or MemoryApprovalBridge(candidate_service=candidate_service, approval_service=approval_service)

    def request_from_candidate(self, candidate_id: str, *, reason: str = "", operator_confirmed: bool = False):
        return self.bridge.request_approval(candidate_id, reason=reason, operator_confirmed=operator_confirmed)

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "memory_approval",
            "approval_scope": "curated_memory_persist",
            "approval_required": True,
            "approved_memory_enabled": True,
            "approval_does_not_persist_automatically": True,
        }
