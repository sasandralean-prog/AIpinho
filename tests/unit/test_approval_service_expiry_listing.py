from datetime import datetime, timedelta, timezone

from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.common.actor import Actor
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore


def _approval(approval_id: str, *, expires_at: str) -> ApprovalRequest:
    now = datetime.now(timezone.utc).isoformat()
    return ApprovalRequest(
        approval_id=approval_id,
        preview_id=f"preview_{approval_id}",
        draft_id=f"draft_{approval_id}",
        session_id=None,
        status="pending",
        actions_requested=["artifact_write_future"],
        approval_scope="future_artifact_write",
        reason="test",
        risk_level="low",
        policy_snapshot={},
        expires_at=expires_at,
        created_at=now,
        updated_at=now,
        created_by=Actor(type="system", id="test"),
        execution_status="not_executed",
    )


def test_list_pending_reconciles_expired_approvals(tmp_path):
    store = ApprovalStore(tmp_path / "approvals")
    expired = _approval(
        "approval_expired",
        expires_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
    )
    active = _approval(
        "approval_active",
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
    )
    store.save(expired)
    store.save(active)

    service = ApprovalService(store=store)

    pending = service.list_approvals(status="pending")

    assert [item.approval_id for item in pending] == ["approval_active"]
    assert store.get("approval_expired").status == "expired"
    assert [event.event_type for event in store.list_events("approval_expired")] == ["approval_expired"]
