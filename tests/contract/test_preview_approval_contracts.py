from __future__ import annotations

import pytest
from pydantic import ValidationError

from aipinho.schemas.approvals.approval_decision import ApprovalDecision
from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.tasks.task_preview import TaskPreview


SNAPSHOT = ApprovalPolicySnapshot(
    policy_decision_id="policy_1",
    policy_status="needs_approval",
    allowed_actions=["patch_preview"],
    denied_actions=[],
    approval_required_for=["apply_patch"],
    granted_capabilities=[],
    denied_capabilities=[],
    workspace_status="confirmed",
    risk_level="medium",
    trace_hash="hash",
)


def test_task_preview_contract_defaults_to_non_execution():
    preview = TaskPreview(
        preview_id="preview_1",
        draft_id="draft_1",
        status="approval_required",
        policy_snapshot=SNAPSHOT,
        created_at="now",
        updated_at="now",
    )
    assert preview.safe_to_execute is False
    assert preview.safe_to_preview is False


def test_task_preview_status_contract_blocks_unknown_status():
    with pytest.raises(ValidationError):
        TaskPreview(
            preview_id="preview_1",
            draft_id="draft_1",
            status="running",
            policy_snapshot=SNAPSHOT,
            created_at="now",
            updated_at="now",
        )


def test_approval_request_contract_is_future_execution_only_by_default():
    approval = ApprovalRequest(
        approval_id="approval_1",
        preview_id="preview_1",
        draft_id="draft_1",
        actions_requested=["apply_patch"],
        policy_snapshot=SNAPSHOT,
        expires_at="later",
        created_at="now",
        updated_at="now",
    )
    assert approval.status == "pending"
    assert approval.approval_scope == "future_execution"
    assert approval.execution_status == "not_executed"


def test_approval_decision_contract_never_executes():
    decision = ApprovalDecision(
        approval_id="approval_1",
        decision="approved",
        decided_at="now",
        policy_snapshot_hash="hash",
    )
    assert decision.execution_status == "not_executed"
