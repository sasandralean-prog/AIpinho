from __future__ import annotations

from datetime import datetime, timezone

import pytest

from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft, TaskDraftWorkspace
from aipinho.services.approvals.approval_lifecycle_service import ApprovalLifecycleService
from aipinho.services.approvals.approval_policy import ApprovalPolicy
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.orchestration.task_contract_draft_service import TaskContractDraftService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.task_lifecycle_service import TaskLifecycleService
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.orchestration.task_preview_store import TaskPreviewStore


def _services(tmp_path):
    draft_store = TaskDraftStore(tmp_path / "drafts")
    preview_store = TaskPreviewStore(tmp_path / "previews")
    approval_store = ApprovalStore(tmp_path / "approvals")
    draft_service = TaskContractDraftService(store=draft_store)
    preview_service = TaskPreviewService(store=preview_store, draft_store=draft_store)
    approval_service = ApprovalService(store=approval_store, preview_service=preview_service, draft_store=draft_store)
    return draft_service, preview_service, approval_service, draft_store, approval_store


def _preview_for_prompt(prompt: str, tmp_path):
    draft_service, preview_service, approval_service, draft_store, approval_store = _services(tmp_path)
    draft = draft_service.create_from_prompt(prompt)
    assert draft is not None
    if draft.approval_required_for or draft.contract_type in {"patch_request", "filesystem_write", "file_modification"}:
        draft.intent_map["patch_plan"] = {
            "files_to_modify": [
                {
                    "path": r"C:\Dev\AIpinho\README.md",
                    "original": "AIpinho",
                    "replacement": "AIpinho",
                }
            ],
            "patch_operations": [
                {
                    "action": "modify_file",
                    "target_path": r"C:\Dev\AIpinho\README.md",
                    "original": "AIpinho",
                    "replacement": "AIpinho",
                }
            ],
            "validation_steps": ["diff_matches_preview"],
        }
        draft.intent_map["concrete_file_operations"] = [
            {"action": "write_files", "target_path": r"C:\Dev\AIpinho\reports\x.md"}
        ]
        draft.intent_map["context_ref"] = "test_context"
        draft.intent_map["validation_plan"] = {"checks": ["diff_matches_preview"]}
        draft.intent_map["rollback_plan"] = {"strategy": "restore_test_fixture"}
        draft.executable_plan_ref = f"patch_plan:{draft.draft_id}"
        draft.expected_outcomes = ["patch_result", "validation_result"]
        draft_store.save(draft)
    preview = preview_service.create_preview_from_draft(draft.draft_id)
    assert preview is not None
    return draft, preview, approval_service, draft_store, approval_store


def _manual_draft(**overrides) -> TaskContractDraft:
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "draft_id": "draft_manual",
        "status": "draft",
        "contract_type": "patch_request",
        "requires_workspace": False,
        "workspace": TaskDraftWorkspace(status="not_required"),
        "requested_actions": [],
        "allowed_actions": [],
        "denied_actions": [],
        "approval_required_for": [],
        "safe_to_execute": False,
        "safe_to_preview": True,
        "policy_decision": {
            "status": "needs_approval",
            "allowed_actions": [],
            "denied_actions": [],
            "approval_required_for": [],
        },
        "created_at": now,
        "updated_at": now,
    }
    data.update(overrides)
    return TaskContractDraft(**data)


def test_task_preview_readonly_is_non_executing(tmp_path):
    draft, preview, _, draft_store, _ = _preview_for_prompt(r"Explique a arquitetura do projeto C:\Dev\AIpinho sem alterar nada", tmp_path)
    assert draft.contract_type == "readonly_analysis"
    assert preview.status == "preview_ready"
    assert preview.safe_to_execute is False
    assert preview.safe_to_preview is True
    assert draft_store.get(draft.draft_id).status == "preview_ready"


def test_task_preview_patch_requires_approval_without_execution(tmp_path):
    draft, preview, _, draft_store, _ = _preview_for_prompt(r"Conserte o bug no projeto C:\Dev\AIpinho", tmp_path)
    assert draft.contract_type == "patch_request"
    assert "apply_patch" in preview.approval_required_for
    assert preview.status == "approval_required"
    assert preview.safe_to_execute is False
    assert draft_store.get(draft.draft_id).status == "approval_required"


def test_task_preview_authorized_protected_root_requires_approval(tmp_path):
    _, preview, approval_service, _, _ = _preview_for_prompt(r"Corrija C:\PinhoabacaxiAI", tmp_path)
    assert preview.status == "approval_required"
    approval = approval_service.create_approval_for_preview(preview.preview_id)
    assert approval.status == "pending"
    assert approval.execution_status == "not_executed"


def test_approval_policy_allows_denied_until_approval_but_blocks_hard_denied():
    policy = ApprovalPolicy().load()
    assert policy.can_request_actions(["apply_patch"], ["apply_patch"], ["apply_patch"])[0] is True
    assert policy.can_request_actions(["apply_patch"], [], ["apply_patch"])[1] == "policy_denied_action"
    assert policy.can_request_actions(["teleport_files"], ["teleport_files"], ["teleport_files"])[1] == "unknown_action"


def test_approval_create_and_approve_never_executes(tmp_path):
    draft, preview, approval_service, draft_store, _ = _preview_for_prompt(r"Conserte o bug no projeto C:\Dev\AIpinho", tmp_path)
    approval = approval_service.create_approval_for_preview(preview.preview_id)
    assert approval.status == "pending"
    assert approval.execution_status == "not_executed"
    assert draft_store.get(draft.draft_id).status == "approval_pending"

    decision, updated = approval_service.approve(approval.approval_id, reason="ok para futura execucao")
    assert decision.decision == "approved"
    assert decision.execution_status == "not_executed"
    assert updated.execution_status == "not_executed"
    assert draft_store.get(draft.draft_id).status == "approved_for_future_execution"


def test_approval_reject_cancel_and_invalid_transition(tmp_path):
    _, preview, approval_service, _, _ = _preview_for_prompt(r"Conserte o bug no projeto C:\Dev\AIpinho", tmp_path)
    approval = approval_service.create_approval_for_preview(preview.preview_id)
    decision, updated = approval_service.reject(approval.approval_id, reason="nao aplicar")
    assert decision.decision == "rejected"
    assert updated.status == "rejected"
    with pytest.raises(ValueError):
        approval_service.approve(approval.approval_id)

    _, preview2, approval_service2, _, _ = _preview_for_prompt(r"Salve um relatorio em C:\Dev\AIpinho\reports\x.md", tmp_path / "second")
    approval2 = approval_service2.create_approval_for_preview(preview2.preview_id)
    decision2, updated2 = approval_service2.cancel(approval2.approval_id, reason="usuario cancelou")
    assert decision2.decision == "cancelled"
    assert updated2.status == "cancelled"


def test_expired_approval_is_not_decidable(tmp_path):
    _, preview, approval_service, _, approval_store = _preview_for_prompt(r"Conserte o bug no projeto C:\Dev\AIpinho", tmp_path)
    approval = approval_service.create_approval_for_preview(preview.preview_id)
    approval.expires_at = "2000-01-01T00:00:00+00:00"
    approval_store.save(approval)

    expired = approval_service.get_approval(approval.approval_id)
    assert expired is not None
    assert expired.status == "expired"
    with pytest.raises(ValueError):
        approval_service.approve(approval.approval_id)


def test_policy_refresh_invalidates_stale_approval_snapshot(tmp_path):
    _, preview, approval_service, _, approval_store = _preview_for_prompt(r"Conserte o bug no projeto C:\Dev\AIpinho", tmp_path)
    approval = approval_service.create_approval_for_preview(preview.preview_id)
    approval.policy_snapshot = ApprovalPolicySnapshot(**approval.policy_snapshot.model_dump())
    approval.policy_snapshot.trace_hash = "stale-policy-snapshot"
    approval_store.save(approval)

    refreshed = approval_service.refresh_policy(approval.approval_id)
    assert refreshed is not None
    assert refreshed.status == "invalidated_by_policy_change"


def test_unknown_action_cannot_be_approved(tmp_path):
    draft_store = TaskDraftStore(tmp_path / "drafts")
    preview_store = TaskPreviewStore(tmp_path / "previews")
    draft = _manual_draft(
        requested_actions=["teleport_files"],
        denied_actions=["teleport_files"],
        approval_required_for=["teleport_files"],
        policy_decision={
            "status": "needs_approval",
            "allowed_actions": [],
            "denied_actions": ["teleport_files"],
            "approval_required_for": ["teleport_files"],
        },
    )
    draft_store.save(draft)
    preview_service = TaskPreviewService(store=preview_store, draft_store=draft_store)
    preview = preview_service.create_preview_from_draft(draft.draft_id)
    assert preview is not None
    assert preview.status == "approval_required"

    approval_service = ApprovalService(store=ApprovalStore(tmp_path / "approvals"), preview_service=preview_service, draft_store=draft_store)
    with pytest.raises(ValueError, match="unknown_action"):
        approval_service.create_approval_for_preview(preview.preview_id)


def test_task_lifecycle_rejects_invalid_transition():
    lifecycle = TaskLifecycleService()
    assert lifecycle.can_transition("approval_required", "approval_pending") is True
    assert lifecycle.can_transition("approved_for_future_execution", "approval_pending") is False
    assert ApprovalLifecycleService().can_transition("pending", "approved") is True
