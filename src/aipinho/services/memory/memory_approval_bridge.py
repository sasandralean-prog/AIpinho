from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.memory.curated_memory import MemoryApprovalResult
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.memory.curated_memory_validator import CuratedMemoryValidator
from aipinho.services.memory.memory_candidate_service import MemoryCandidateService


class MemoryApprovalBridge:
    def __init__(self, approval_service: ApprovalService | None = None, candidate_service: MemoryCandidateService | None = None) -> None:
        self.approval_service = approval_service or ApprovalService()
        self.candidate_service = candidate_service or MemoryCandidateService()

    def request_approval(self, candidate_id: str, *, reason: str = "", operator_confirmed: bool = False) -> MemoryApprovalResult:
        candidate = self.candidate_service.get_candidate(candidate_id)
        validation = CuratedMemoryValidator().validate_candidate(candidate)
        if not validation.allowed:
            return MemoryApprovalResult(status="blocked", candidate_id=candidate_id, blocked_reasons=validation.blocked_reasons, warnings=validation.warnings)
        now = datetime.now(timezone.utc)
        metadata = {
            "candidate_id": candidate.candidate_id,
            "kind": candidate.kind,
            "scope": candidate.scope.model_dump() if hasattr(candidate.scope, "model_dump") else candidate.scope.dict(),
            "source": candidate.source.model_dump() if hasattr(candidate.source, "model_dump") else candidate.source.dict(),
            "evidence_ids": [item.evidence_id for item in candidate.evidence],
            "confidence": candidate.confidence,
            "risk": candidate.risk.model_dump() if hasattr(candidate.risk, "model_dump") else candidate.risk.dict(),
            "dedupe_status": candidate.dedupe.status,
            "conflict_status": "conflict" if candidate.conflict.has_conflict else "none",
            "operator_confirmed_at_request": operator_confirmed,
        }
        approval = ApprovalRequest(
            approval_id=f"approval_{uuid4().hex}",
            preview_id=candidate.candidate_id,
            draft_id=candidate.candidate_id,
            session_id=None,
            status="pending",
            actions_requested=["persist_curated_memory"],
            approval_scope="curated_memory_persist",
            reason=reason or "Persist curated memory from valid candidate.",
            risk_level=candidate.risk.level,
            policy_snapshot=ApprovalPolicySnapshot(
                policy_status="needs_approval",
                allowed_actions=["persist_curated_memory"],
                denied_actions=[],
                approval_required_for=["persist_curated_memory"],
                workspace_status="ok",
                risk_level=candidate.risk.level,
                trace_hash=candidate.dedupe.normalized_hash,
                config_versions={"memory": metadata},
            ),
            expires_at=(now + timedelta(minutes=60)).isoformat(),
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            created_by=Actor(type="system", id="memory_approval_bridge"),
            trace=[{"stage": "memory_approval_create", "decision": "pending", "reason": "approval_created_without_persistence"}],
            execution_status="not_executed",
        )
        self.approval_service.store.save(approval)
        self.approval_service.append_event(approval.approval_id, "approval_created", "Memory approval created; no memory persisted.", {"candidate_id": candidate_id, "approval_scope": "curated_memory_persist"})
        return MemoryApprovalResult(status="pending", approval_id=approval.approval_id, candidate_id=candidate_id, persisted=False)
