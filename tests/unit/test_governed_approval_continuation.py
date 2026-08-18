from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft, TaskDraftWorkspace
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.approvals.approval_task_continuation_service import ApprovalTaskContinuationService
from aipinho.services.chat.chat_approval_command_service import ChatApprovalCommandService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.orchestration.task_preview_store import TaskPreviewStore
from aipinho.services.runtime.task_queue_service import TaskQueueService
from aipinho.services.runtime.task_run_store import TaskRunStore


def _policy_snapshot() -> ApprovalPolicySnapshot:
    return ApprovalPolicySnapshot(
        policy_status="needs_approval",
        allowed_actions=["write_files"],
        denied_actions=[],
        approval_required_for=["write_files"],
        trace_hash="test-trace",
    )


def _approval(
    approval_id: str,
    *,
    run_id: str = "task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    workspace_path: str = r"C:\Workspace\Allowed",
    status: str = "pending",
    actions: list[str] | None = None,
) -> ApprovalRequest:
    task_id = run_id.replace("task_run_", "task_", 1) if run_id.startswith("task_run_") else run_id
    now = datetime.now(timezone.utc)
    return ApprovalRequest(
        approval_id=approval_id,
        preview_id=f"preview_{approval_id}",
        draft_id=f"draft_{approval_id}",
        run_id=run_id,
        task_id=task_id,
        workspace_path=workspace_path,
        operation_type="governed_file_write",
        status=status,  # type: ignore[arg-type]
        actions_requested=actions or ["write_files"],
        approval_scope="single_action",
        risk_level="medium",
        policy_snapshot=_policy_snapshot(),
        expires_at=(now + timedelta(hours=1)).isoformat(),
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
    )


def _run(run_id: str = "task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", approval_id: str = "approval_test") -> TaskRun:
    task_id = run_id.replace("task_run_", "task_", 1) if run_id.startswith("task_run_") else f"task_{run_id}"
    operation_id = run_id.replace("task_run_", "op_", 1) if run_id.startswith("task_run_") else f"op_{run_id}"
    return TaskRun(
        run_id=run_id,
        task_id=task_id,
        operation_id=operation_id,
        task_run_id=run_id,
        bootstrap_context={
            "task_id": task_id,
            "operation_id": operation_id,
            "task_run_id": run_id,
            "runtime_profile": "governed",
            "workspace": r"C:\Workspace\Allowed",
            "operation_type": "governed_file_write",
            "contract_type": "patch_request",
            "context": {
                "requires_task": True,
                "bootstrap_invariant": "execution_requires_universal_task",
            },
        },
        source_type="preview",
        session_id="chat_test",
        workspace=r"C:\Workspace\Allowed",
        contract_type="patch_request",
        operation_type="governed_file_write",
        requested_actions=["write_files"],
        approval_id=approval_id,
        blocked_reasons=["approval_required"],
        status="waiting_input",
        auto_run_requested=False,
        policy_snapshot={"status": "needs_approval", "approval_required_for": ["write_files"]},
        plan=TaskRunPlan(
            plan_id="plan_test",
            contract_type="patch_request",
            status="ready",
            steps=[
                TaskRunStep(
                    step_id="step_01",
                    step_type="write_file",
                    action="write_files",
                    required=True,
                )
            ],
        ),
    )


def _draft(draft_id: str = "draft_test", session_id: str = "chat_test") -> TaskContractDraft:
    now = datetime.now(timezone.utc).isoformat()
    return TaskContractDraft(
        draft_id=draft_id,
        session_id=session_id,
        status="approval_required",
        intent_map={
            "risk": "medium",
            "source": "test",
            "target_paths": [r"C:\Workspace\Allowed\app.txt"],
            "context_ref": "test_context",
            "validation_plan": {"checks": ["diff_matches_preview"]},
            "rollback_plan": {"strategy": "restore_test_fixture"},
            "patch_plan": {
                "files_to_modify": [
                    {
                        "path": r"C:\Workspace\Allowed\app.txt",
                        "original": "old",
                        "replacement": "new",
                    }
                ],
                "patch_operations": [
                    {
                        "action": "modify_file",
                        "target_path": r"C:\Workspace\Allowed\app.txt",
                        "original": "old",
                        "replacement": "new",
                    }
                ],
                "validation_steps": ["diff_matches_preview"],
            },
        },
        policy_decision={
            "decision_id": f"policy_{draft_id}",
            "status": "needs_approval",
            "allowed_actions": [],
            "denied_actions": [],
            "approval_required_for": ["write_files"],
            "granted_capabilities": [],
            "denied_capabilities": [],
        },
        contract_type="patch_request",
        operation_type="governed_file_write",
        intent_type="test_governed_write",
        runtime_profile="governed",
        capabilities_required=["write_files"],
        source_scope="test_harness",
        requires_workspace=True,
        workspace=TaskDraftWorkspace(path=r"C:\Workspace\Allowed", status="confirmed"),
        requested_actions=["write_files"],
        allowed_actions=[],
        denied_actions=[],
        approval_required_for=["write_files"],
        executable_plan_ref=f"{draft_id}:patch_plan",
        expected_outcomes=["patch_result", "validation_result"],
        safe_to_execute=False,
        safe_to_preview=True,
        trace=[{"source": "test_harness", "stage": "draft"}],
        created_at=now,
        updated_at=now,
    )


def _approval_service_with_preview(tmp_path):
    draft_store = TaskDraftStore(root=tmp_path / "drafts")
    preview_store = TaskPreviewStore(root=tmp_path / "previews")
    preview_service = TaskPreviewService(store=preview_store, draft_store=draft_store)
    approval_store = ApprovalStore(root=tmp_path / "approvals")
    approvals = ApprovalService(store=approval_store, preview_service=preview_service, draft_store=draft_store)
    return approvals, draft_store, preview_service


def _create_real_pending_approval(
    tmp_path,
    *,
    session_id: str = "chat_test",
    run_id: str = "task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
    draft_id: str = "draft_test",
) -> tuple[ApprovalService, ApprovalRequest]:
    task_id = run_id.replace("task_run_", "task_", 1) if run_id.startswith("task_run_") else f"task_{run_id}"
    approvals, draft_store, preview_service = _approval_service_with_preview(tmp_path)
    draft = _draft(draft_id=draft_id, session_id=session_id)
    draft_store.save(draft)
    preview = preview_service.create_preview_from_draft(draft.draft_id)
    assert preview is not None
    approval = approvals.create_approval_for_preview(preview.preview_id, actions=["write_files"], reason="test_real_preview")
    linked = approvals.attach_runtime_context(approval.approval_id, run_id=run_id, task_id=task_id, workspace_path=r"C:\Workspace\Allowed")
    assert linked is not None
    return approvals, linked


def test_approved_approval_releases_task_run_for_governed_queue(tmp_path):
    run_store = TaskRunStore(root=tmp_path / "runs")
    approval_store = ApprovalStore(root=tmp_path / "approvals")
    approval_service = ApprovalService(store=approval_store)
    run = _run()
    run_store.create_run(run)
    approval = _approval("approval_test", status="approved")
    approval_store.save(approval)

    result = ApprovalTaskContinuationService(
        approvals=approval_service,
        store=run_store,
    ).after_decision(approval, auto_process=False)

    updated = run_store.get_run(run.run_id)
    assert result["status"] == "ok"
    assert result["resumed"] is True
    assert updated is not None
    assert updated.auto_run_requested is True
    assert "approval_required" not in updated.blocked_reasons
    assert updated.approval_snapshot["approval_id"] == "approval_test"


def test_rejected_approval_cancels_task_run_without_execution(tmp_path):
    run_store = TaskRunStore(root=tmp_path / "runs")
    approval_store = ApprovalStore(root=tmp_path / "approvals")
    approval_service = ApprovalService(store=approval_store)
    run = _run()
    run_store.create_run(run)
    approval = _approval("approval_test", status="rejected")
    approval_store.save(approval)

    result = ApprovalTaskContinuationService(
        approvals=approval_service,
        store=run_store,
    ).after_decision(approval, auto_process=False)

    updated = run_store.get_run(run.run_id)
    events = run_store.get_events(run.run_id)
    assert result["status"] == "ok"
    assert result["resumed"] is False
    assert result["cancelled"] is True
    assert updated is not None
    assert updated.status == "cancelled"
    assert updated.auto_run_requested is False
    assert "approval_required" not in updated.blocked_reasons
    assert any(event.type == "task_cancelled_after_denial" for event in events)


def test_queue_reconcile_approved_approval_is_idempotent_release(tmp_path):
    run_store = TaskRunStore(root=tmp_path / "runs")
    approval_store = ApprovalStore(root=tmp_path / "approvals")
    approval_service = ApprovalService(store=approval_store)
    run = _run()
    run_store.create_run(run)
    approval_store.save(_approval("approval_test", status="approved"))

    result = TaskQueueService(store=run_store, approvals=approval_service).reconcile()

    updated = run_store.get_run(run.run_id)
    assert result.status == "ok"
    assert updated is not None
    assert updated.auto_run_requested is True
    assert "approval_required" not in updated.blocked_reasons


def test_queue_reconcile_rejected_approval_cancels_without_blocking(tmp_path):
    run_store = TaskRunStore(root=tmp_path / "runs")
    approval_store = ApprovalStore(root=tmp_path / "approvals")
    approval_service = ApprovalService(store=approval_store)
    run = _run()
    run_store.create_run(run)
    approval_store.save(_approval("approval_test", status="rejected"))

    result = TaskQueueService(store=run_store, approvals=approval_service).reconcile()

    updated = run_store.get_run(run.run_id)
    assert result.status == "ok"
    assert updated is not None
    assert updated.status == "blocked"
    assert "approval_denied" in updated.blocked_reasons
    assert updated.block_cause is not None
    assert updated.block_cause.blocked_stage == "approval_denied"
    assert updated.auto_run_requested is False


def test_safe_batch_rejects_cross_task_or_unsafe_actions(tmp_path):
    approval_store = ApprovalStore(root=tmp_path / "approvals")
    service = ApprovalService(store=approval_store)
    approval_store.save(_approval("approval_a", run_id="task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"))
    approval_store.save(_approval("approval_b", run_id="task_run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"))
    approval_store.save(_approval("approval_c", actions=["delete_file"]))

    with pytest.raises(ValueError, match="batch_cross_task_not_allowed"):
        service.approve_batch(["approval_a", "approval_b"], safe_only=True)

    with pytest.raises(ValueError, match="batch_contains_non_safe_action"):
        service.approve_batch(["approval_c"], safe_only=True)


def test_chat_approval_command_requires_explicit_approval_or_task_identifier() -> None:
    parser = ChatApprovalCommandService()

    assert parser.parse("pode aprovar isso para mim") is None
    explicit = parser.parse("aprovar approval_abc123")
    batch = parser.parse("aprovar todas task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")

    assert explicit is not None
    assert explicit.action == "approve"
    assert explicit.target_id == "approval_abc123"
    assert explicit.scope == "single_action"
    assert batch is not None
    assert batch.scope == "safe_batch"


def test_chat_approval_command_approves_specific_pending_approval(tmp_path):
    run_store = TaskRunStore(root=tmp_path / "runs")
    approvals, approval = _create_real_pending_approval(tmp_path)
    continuation = ApprovalTaskContinuationService(approvals=approvals, store=run_store)
    run = _run(approval_id=approval.approval_id)
    run_store.create_run(run)

    response = ChatApprovalCommandService(approvals=approvals, continuation=continuation).handle(
        "chat_test",
        f"APROVAR {approval.approval_id}",
    )

    updated = run_store.get_run(run.run_id)
    approval = approvals.get_approval(approval.approval_id)
    assert response is not None
    assert response.status == "ok"
    assert approval is not None
    assert approval.status == "approved"
    assert updated is not None
    assert updated.auto_run_requested is True


def test_chat_approval_command_denies_specific_pending_approval(tmp_path):
    run_store = TaskRunStore(root=tmp_path / "runs")
    approvals, approval = _create_real_pending_approval(tmp_path)
    continuation = ApprovalTaskContinuationService(approvals=approvals, store=run_store)
    run = _run(approval_id=approval.approval_id)
    run_store.create_run(run)

    response = ChatApprovalCommandService(approvals=approvals, continuation=continuation).handle(
        "chat_test",
        f"NEGAR {approval.approval_id}",
    )

    updated = run_store.get_run(run.run_id)
    approval = approvals.get_approval(approval.approval_id)
    assert response is not None
    assert response.status == "ok"
    assert approval is not None
    assert approval.status == "rejected"
    assert updated is not None
    assert updated.status == "cancelled"


def test_chat_approval_approve_last_single_pending_works(tmp_path):
    run_store = TaskRunStore(root=tmp_path / "runs")
    approvals, approval = _create_real_pending_approval(tmp_path)
    continuation = ApprovalTaskContinuationService(approvals=approvals, store=run_store)
    run_store.create_run(_run(approval_id=approval.approval_id))

    response = ChatApprovalCommandService(approvals=approvals, continuation=continuation).handle(
        "chat_test",
        "APROVAR ULTIMA ACAO",
    )

    updated = approvals.get_approval(approval.approval_id)
    assert response is not None
    assert response.status == "ok"
    assert updated is not None
    assert updated.status == "approved"


def test_chat_approval_approve_last_multiple_pending_is_ambiguous(tmp_path):
    approvals, first = _create_real_pending_approval(
        tmp_path,
        run_id="task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        draft_id="draft_first",
    )
    second_draft = _draft(draft_id="draft_second", session_id="chat_test")
    approvals.draft_store.save(second_draft)
    preview = approvals.preview_service.create_preview_from_draft(second_draft.draft_id)
    assert preview is not None
    second = approvals.create_approval_for_preview(preview.preview_id, actions=["write_files"], reason="test_second")
    approvals.attach_runtime_context(
        second.approval_id,
        run_id="task_run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        task_id="task_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        workspace_path=r"C:\Workspace\Allowed",
    )

    response = ChatApprovalCommandService(approvals=approvals).handle("chat_test", "APROVAR")

    assert response is not None
    assert response.status == "blocked"
    assert response.policy["reason_code"] == "approval_ambiguous_decision"
    assert approvals.get_approval(first.approval_id).status == "pending"  # type: ignore[union-attr]
    assert approvals.get_approval(second.approval_id).status == "pending"  # type: ignore[union-attr]


def test_chat_approval_show_preview_returns_details(tmp_path):
    approvals, approval = _create_real_pending_approval(tmp_path)

    response = ChatApprovalCommandService(approvals=approvals).handle(
        "chat_test",
        f"MOSTRAR PREVIEW {approval.approval_id}",
    )

    assert response is not None
    assert response.status == "ok"
    assert response.approval_id == approval.approval_id
    assert "APPROVAL DETAILS" in response.message


def test_chat_approval_delete_requires_explicit_delete_phrase(tmp_path):
    approval_store = ApprovalStore(root=tmp_path / "approvals")
    approvals = ApprovalService(store=approval_store)
    approval_store.save(_approval("approval_delete", actions=["delete_file"]))

    blocked = ChatApprovalCommandService(approvals=approvals).handle(
        "chat_test",
        "APROVAR approval_delete",
    )
    assert blocked is not None
    assert blocked.status == "blocked"
    assert "specific_approval_phrase_required:delete" in blocked.message


def test_chat_approval_unknown_id_returns_structured_block() -> None:
    response = ChatApprovalCommandService().handle(
        "chat_test",
        "APROVAR approval_inexistente_sprint21",
    )

    assert response is not None
    assert response.status == "blocked"
    assert response.operation_type == "approval_command"
    assert response.policy["reason_code"] == "approval_not_found"
