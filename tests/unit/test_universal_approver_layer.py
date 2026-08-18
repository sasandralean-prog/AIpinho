from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.approvals.universal_approver import (
    UniversalApprovalTextRequest,
    UniversalApproverUpsertRequest,
)
from aipinho.schemas.common.actor import Actor
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.approvals.universal_approver_service import UniversalApproverService


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _policy_snapshot(actions: list[str]) -> ApprovalPolicySnapshot:
    return ApprovalPolicySnapshot(
        policy_decision_id="policy_universal_test",
        policy_status="ask",
        allowed_actions=[],
        denied_actions=[],
        approval_required_for=actions,
        workspace_status="confirmed",
        risk_level="medium",
        trace_hash="trace_hash",
    )


def _approval(
    approval_id: str,
    *,
    actions: list[str],
    expires_delta: timedelta | None = None,
    status: str = "pending",
) -> ApprovalRequest:
    now = _now()
    return ApprovalRequest(
        approval_id=approval_id,
        preview_id=f"preview_{approval_id}",
        draft_id=f"draft_{approval_id}",
        session_id="chat_universal",
        workspace_path=r"C:\Work\Universal",
        operation_type="patch_request",
        contract_type="patch_request",
        runtime_profile="governed_patch",
        target_paths=[r"C:\Work\Universal"],
        expected_outcomes=["patch_result", "validation_result"],
        executable_plan_ref=f"patch_plan:{approval_id}",
        preview={"available": True, "summary": "unit test preview"},
        status=status,
        actions_requested=actions,
        approval_scope="future_execution",
        reason="unit test",
        risk_level="medium",
        policy_snapshot=_policy_snapshot(actions),
        expires_at=(now + (expires_delta or timedelta(minutes=30))).isoformat(),
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        created_by=Actor(type="system", id="unit_test"),
    )


def _service(tmp_path: Path) -> UniversalApproverService:
    approvals = ApprovalService(store=ApprovalStore(tmp_path / "approvals"))
    return UniversalApproverService(
        approval_service=approvals,
        store_path=tmp_path / "universal_approvers.json",
    )


def _save_approval(service: UniversalApproverService, approval: ApprovalRequest) -> ApprovalRequest:
    service.approvals.store.save(approval)
    return approval


def _upsert(
    service: UniversalApproverService,
    approver_id: str,
    *,
    trust_level: str = "L1",
    capabilities: dict[str, list[str]] | None = None,
    status: str = "active",
    approver_type: str = "external_adapter",
) -> None:
    service.upsert_approver(
        UniversalApproverUpsertRequest(
            approver_id=approver_id,
            display_name=approver_id.title(),
            approver_type=approver_type,
            trust_level=trust_level,
            capabilities=capabilities or {"filesystem": ["approve"], "patch": ["approve"]},
            status=status,
        )
    )


def test_universal_approver_registers_and_lists(tmp_path: Path):
    service = _service(tmp_path)
    _upsert(service, "external-reviewer", capabilities={"reports": ["approve", "review"]})

    approvers = {item.approver_id: item for item in service.list_approvers()}

    assert "external-reviewer" in approvers
    assert approvers["external-reviewer"].capabilities["reports"] == ["approve", "review"]
    assert all(item.metadata.get("api_key") is None for item in approvers.values())


def test_gemini_text_approval_records_origin_signature_and_same_pipeline(tmp_path: Path):
    service = _service(tmp_path)
    _upsert(service, "gemini", capabilities={"patch": ["approve"], "contracts": ["approve"]})
    _save_approval(service, _approval("approval_gemini", actions=["apply_patch"]))

    result = service.decide_from_text(
        "approval_gemini",
        UniversalApprovalTextRequest(
            approver_id="gemini",
            text="Approved. The patch preview can continue through AIpinho.",
            session_id="chat_universal",
            collaboration_session="collab_test",
            requested_by="codex",
            reason="review passed",
        ),
    )

    stored = service.approvals.get_approval("approval_gemini")
    events = [event.event_type for event in service.approvals.list_events("approval_gemini")]

    assert result.status == "ok"
    assert result.external_may_execute is False
    assert result.authority == "AIpinho"
    assert stored is not None
    assert stored.status == "approved"
    assert stored.approval_authority == "AIpinho"
    assert stored.approval_origin is not None
    assert stored.approval_origin.origin_id == "gemini"
    assert stored.approval_signature is not None
    assert stored.approval_signature.approver_id == "gemini"
    assert "universal_approval_decision_received" in events
    assert "universal_approval_signature_created" in events
    assert "universal_approval_decision_accepted" in events


def test_codex_text_approval_uses_same_contract_without_provider_branch(tmp_path: Path):
    service = _service(tmp_path)
    _upsert(service, "codex", capabilities={"filesystem": ["approve"], "contracts": ["approve"]})
    _save_approval(service, _approval("approval_codex", actions=["write_files"]))

    result = service.decide_from_text(
        "approval_codex",
        UniversalApprovalTextRequest(approver_id="codex", text="Autorizo a continuidade pelo runtime governado."),
    )

    stored = service.approvals.get_approval("approval_codex")
    assert result.status == "ok"
    assert stored is not None
    assert stored.status == "approved"
    assert stored.approval_origin is not None
    assert stored.approval_origin.approval_authority == "AIpinho"


def test_capability_denied_blocks_without_approval_decision(tmp_path: Path):
    service = _service(tmp_path)
    _upsert(
        service,
        "human-reviewer",
        trust_level="L2",
        approver_type="human",
        capabilities={"shell": ["review"]},
    )
    _save_approval(service, _approval("approval_shell_capability", actions=["run_command"]))

    result = service.decide_from_text(
        "approval_shell_capability",
        UniversalApprovalTextRequest(approver_id="human-reviewer", text="approved"),
    )

    stored = service.approvals.get_approval("approval_shell_capability")
    assert result.status == "blocked"
    assert result.reason_code == "capability_denied"
    assert stored is not None
    assert stored.status == "pending"
    assert stored.approval_origin is None


def test_trust_level_denied_blocks_without_approval_decision(tmp_path: Path):
    service = _service(tmp_path)
    _upsert(service, "external-shell-reviewer", trust_level="L1", capabilities={"shell": ["approve"]})
    _save_approval(service, _approval("approval_shell_trust", actions=["run_command"]))

    result = service.decide_from_text(
        "approval_shell_trust",
        UniversalApprovalTextRequest(approver_id="external-shell-reviewer", text="approved"),
    )

    assert result.status == "blocked"
    assert result.reason_code == "trust_level_denied"
    assert service.approvals.get_approval("approval_shell_trust").status == "pending"


def test_disabled_revoked_and_unknown_approvers_are_rejected(tmp_path: Path):
    service = _service(tmp_path)
    _upsert(service, "disabled-bot", status="disabled")
    _upsert(service, "revoked-bot", status="revoked")
    _save_approval(service, _approval("approval_disabled", actions=["write_files"]))
    _save_approval(service, _approval("approval_revoked", actions=["write_files"]))
    _save_approval(service, _approval("approval_unknown", actions=["write_files"]))

    disabled = service.decide_from_text(
        "approval_disabled",
        UniversalApprovalTextRequest(approver_id="disabled-bot", text="approved"),
    )
    revoked = service.decide_from_text(
        "approval_revoked",
        UniversalApprovalTextRequest(approver_id="revoked-bot", text="approved"),
    )
    unknown = service.decide_from_text(
        "approval_unknown",
        UniversalApprovalTextRequest(approver_id="missing-bot", text="approved"),
    )

    assert disabled.reason_code == "approver_disabled"
    assert revoked.reason_code == "approver_revoked"
    assert unknown.reason_code == "unknown_approver"


def test_reject_text_records_rejection_signature(tmp_path: Path):
    service = _service(tmp_path)
    _upsert(service, "gemini-reviewer", capabilities={"patch": ["approve"]})
    _save_approval(service, _approval("approval_reject", actions=["apply_patch"]))

    result = service.decide_from_text(
        "approval_reject",
        UniversalApprovalTextRequest(approver_id="gemini-reviewer", text="Denied. Risk is too high."),
    )

    stored = service.approvals.get_approval("approval_reject")
    assert result.status == "ok"
    assert result.decision == "rejected"
    assert stored is not None
    assert stored.status == "rejected"
    assert stored.approval_signature is not None


def test_double_approval_replay_is_blocked(tmp_path: Path):
    service = _service(tmp_path)
    _upsert(service, "reviewer", capabilities={"filesystem": ["approve"]})
    _save_approval(service, _approval("approval_replay", actions=["write_files"]))

    first = service.decide_from_text(
        "approval_replay",
        UniversalApprovalTextRequest(approver_id="reviewer", text="approved"),
    )
    second = service.decide_from_text(
        "approval_replay",
        UniversalApprovalTextRequest(approver_id="reviewer", text="approved again"),
    )

    assert first.status == "ok"
    assert second.status == "blocked"
    assert "approval_not_pending" in (second.reason_code or "")


def test_expired_approval_cannot_be_approved(tmp_path: Path):
    service = _service(tmp_path)
    _upsert(service, "reviewer", capabilities={"filesystem": ["approve"]})
    _save_approval(
        service,
        _approval("approval_expired_universal", actions=["write_files"], expires_delta=timedelta(minutes=-5)),
    )

    result = service.decide_from_text(
        "approval_expired_universal",
        UniversalApprovalTextRequest(approver_id="reviewer", text="approved"),
    )

    stored = service.approvals.get_approval("approval_expired_universal")
    assert result.status == "blocked"
    assert result.reason_code == "approval_expired"
    assert stored is not None
    assert stored.status == "expired"


def test_timeline_and_mobile_view_share_universal_approval_source(tmp_path: Path):
    service = _service(tmp_path)
    _upsert(service, "timeline-reviewer", capabilities={"reports": ["approve"]})
    _save_approval(service, _approval("approval_timeline", actions=["generate_report"]))
    service.decide_from_text(
        "approval_timeline",
        UniversalApprovalTextRequest(approver_id="timeline-reviewer", text="approved"),
    )

    timeline = service.timeline()
    mobile = service.mobile_view_model()

    assert timeline["authority"] == "AIpinho"
    assert timeline["items"][0]["approval_id"] == "approval_timeline"
    assert timeline["items"][0]["signature"] is not None
    assert mobile["cards"][0]["card_type"] == "universal_approvers"
    assert mobile["cards"][1]["card_type"] == "approval_timeline"
