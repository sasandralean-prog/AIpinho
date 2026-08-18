from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.common.actor import Actor
from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft, TaskDraftWorkspace
from aipinho.schemas.tasks.task_preview import TaskPreview
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.chat.chat_approval_command_service import ChatApprovalCommandService
from aipinho.services.orchestration.executable_plan_service import ExecutablePlanService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.orchestration.task_preview_store import TaskPreviewStore


class _ApprovalPolicy:
    def ttl_minutes(self) -> int:
        return 30

    def require_policy_snapshot(self) -> bool:
        return True

    def can_request_actions(self, actions, approval_required_for, denied_actions):
        if not actions:
            return False, "no_actions_requested"
        if any(action not in approval_required_for for action in actions):
            return False, "action_not_marked_as_approval_required"
        return True, "ok"

    def blocked_actions_this_sprint(self):
        return set()

    def safe_batch_excluded_actions(self):
        return set()


class _Continuation:
    def __init__(self, resume):
        self.resume = resume

    def after_decision(self, approval, auto_process=True):
        return self.resume

    def approve_safe_batch_for_task(self, *args, **kwargs):
        return {"status": "blocked", "reason_code": "not_used"}

    def _process_queue_if_enabled(self):
        return {"status": "disabled"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _stores(tmp_path: Path):
    draft_store = TaskDraftStore(tmp_path / "drafts")
    preview_store = TaskPreviewStore(tmp_path / "previews")
    approval_store = ApprovalStore(tmp_path / "approvals")
    preview_service = TaskPreviewService(store=preview_store, draft_store=draft_store)
    approvals = ApprovalService(
        store=approval_store,
        preview_service=preview_service,
        draft_store=draft_store,
        policy=_ApprovalPolicy(),
    )
    return draft_store, preview_service, approvals


def _draft(
    *,
    draft_id: str = "draft_project_generation",
    intent_map: dict | None = None,
    requested_actions: list[str] | None = None,
    approval_required_for: list[str] | None = None,
    contract_type: str = "project_generation",
    operation_type: str = "project_generation",
    runtime_profile: str = "project_generation",
    executable_plan_ref: str | None = None,
) -> TaskContractDraft:
    actions = requested_actions or ["write_files"]
    base_intent = {
        "risk": "medium",
        "target_path": r"C:\Work\App",
        "context_ref": "test_context",
        "validation_plan": {"checks": ["expected_outputs_present"]},
        "rollback_plan": {"strategy": "delete_created_test_files"},
    }
    if intent_map:
        base_intent.update(intent_map)
    return TaskContractDraft(
        draft_id=draft_id,
        session_id="chat_test",
        status="approval_required",
        intent_map=base_intent,
        policy_decision={
            "decision_id": "policy_test",
            "status": "ask",
            "allowed_actions": [],
            "denied_actions": [],
            "approval_required_for": approval_required_for or actions,
            "granted_capabilities": [],
            "denied_capabilities": [],
        },
        contract_type=contract_type,
        operation_type=operation_type,
        intent_type="implementation_request",
        runtime_profile=runtime_profile,
        capabilities_required=["write_workspace"],
        source_scope="chat",
        requires_workspace=True,
        workspace=TaskDraftWorkspace(path=r"C:\Work\App", status="confirmed"),
        requested_actions=actions,
        allowed_actions=[],
        denied_actions=[],
        approval_required_for=approval_required_for or actions,
        executable_plan_ref=executable_plan_ref,
        expected_outcomes=["project_generation", "validation_result"],
        safe_to_execute=False,
        safe_to_preview=True,
        trace=[{"stage": "test"}],
        created_at=_now(),
        updated_at=_now(),
    )


def _policy_snapshot() -> ApprovalPolicySnapshot:
    return ApprovalPolicySnapshot(
        policy_decision_id="policy_test",
        policy_status="ask",
        approval_required_for=["write_files"],
        workspace_status="confirmed",
        risk_level="medium",
        trace_hash="trace_hash",
    )


def _approval(approval_id: str, *, session_id: str = "chat_test", task_id: str = "task_run_test") -> ApprovalRequest:
    now = datetime.now(timezone.utc)
    return ApprovalRequest(
        approval_id=approval_id,
        preview_id="preview_test",
        draft_id="draft_test",
        task_id=task_id,
        session_id=session_id,
        workspace_path=r"C:\Work\App",
        operation_type="project_generation",
        contract_type="project_generation",
        runtime_profile="project_generation",
        target_paths=[r"C:\Work\App"],
        expected_outcomes=["project_generation", "validation_result"],
        executable_plan_ref="project_generation_plan:draft_test",
        preview={"available": True},
        status="pending",
        actions_requested=["write_files"],
        approval_scope="future_execution",
        reason="test",
        risk_level="medium",
        policy_snapshot=_policy_snapshot(),
        expires_at=(now + timedelta(minutes=30)).isoformat(),
        created_at=now.isoformat(),
        updated_at=now.isoformat(),
        created_by=Actor(type="user", id="test"),
    )


def _create_real_approval(draft_store: TaskDraftStore, preview_service: TaskPreviewService, approvals: ApprovalService, approval_id: str) -> ApprovalRequest:
    plan = {
        "target_workspace": r"C:\Work\App",
        "files_to_create": [{"path": r"C:\Work\App\app.txt", "content": "ok"}],
        "validation_steps": ["file_exists"],
        "expected_outputs": ["app.txt"],
    }
    draft_store.save(
        _draft(
            draft_id=f"draft_{approval_id}",
            intent_map={"risk": "medium", "target_path": r"C:\Work\App", "project_generation_plan": plan},
            executable_plan_ref=f"project_generation_plan:draft_{approval_id}",
        )
    )
    preview = preview_service.create_preview_from_draft(f"draft_{approval_id}")
    approval = approvals.create_approval_for_preview(preview.preview_id, actions=["write_files"])
    original_id = approval.approval_id
    approval.approval_id = approval_id
    approval.task_id = "task_test"
    approvals.store.save(approval)
    if original_id != approval_id:
        original_path = approvals.store._path(original_id)
        if original_path.exists():
            original_path.unlink()
    return approval


def test_approval_not_created_without_executable_plan(tmp_path: Path):
    draft_store, preview_service, approvals = _stores(tmp_path)
    draft_store.save(_draft())
    preview = preview_service.create_preview_from_draft("draft_project_generation")

    assert preview is not None
    assert "missing_project_generation_plan" in preview.warnings
    with pytest.raises(ValueError, match="missing_project_generation_plan"):
        approvals.create_approval_for_preview(preview.preview_id, actions=["write_files"])


def test_project_generation_preview_with_plan_creates_approval(tmp_path: Path):
    draft_store, preview_service, approvals = _stores(tmp_path)
    plan = {
        "target_workspace": r"C:\Work\App",
        "files_to_create": [{"path": r"C:\Work\App\app.txt", "content": "ok"}],
        "validation_steps": ["file_exists"],
        "expected_outputs": ["app.txt"],
    }
    draft_store.save(
        _draft(
            draft_id="draft_with_plan",
            intent_map={"risk": "medium", "target_path": r"C:\Work\App", "project_generation_plan": plan},
            executable_plan_ref="project_generation_plan:draft_with_plan",
        )
    )
    preview = preview_service.create_preview_from_draft("draft_with_plan")

    approval = approvals.create_approval_for_preview(preview.preview_id, actions=["write_files"])

    assert approval.draft_id == "draft_with_plan"
    assert approval.executable_plan_ref == "project_generation_plan:draft_with_plan"
    assert approval.expected_outcomes == ["project_generation", "validation_result"]


def test_target_paths_only_real_paths():
    draft = _draft()
    preview = TaskPreview(
        preview_id="preview_paths",
        draft_id=draft.draft_id,
        session_id=draft.session_id,
        status="approval_required",
        contract_type=draft.contract_type,
        summary="test",
        requested_actions=["write_files"],
        approval_required_for=["write_files"],
        potential_side_effects=["write_files: Pode criar ou alterar arquivos se aprovado em runtime futuro."],
        policy_snapshot=_policy_snapshot(),
        created_at=_now(),
        updated_at=_now(),
    )

    paths = ExecutablePlanService().real_target_paths(draft, preview)

    assert paths == [r"C:\Work\App"]


def test_patch_draft_uses_canonical_executable_patch_plan():
    draft = _draft(
        draft_id="draft_patch_execution",
        contract_type="patch_request",
        operation_type="patch_request",
        runtime_profile="patch",
        executable_plan_ref="executable_patch_plan:draft_patch_execution",
        intent_map={
            "risk": "medium",
            "target_path": r"C:\Work\App\src\decoder.py",
            "target_paths": [r"C:\Work\App\src\decoder.py"],
            "context_ref": "test_context",
            "validation_plan": {"checks": ["patch_result", "validation_result"]},
            "rollback_plan": {"strategy": "restore_previous_hunks"},
            "execution_intent": {
                "intent_id": "execution_intent_test",
                "status": "complete",
                "workspace": r"C:\Work\App",
                "target_files": [r"C:\Work\App\src\decoder.py"],
                "target_symbols": ["AdaptiveDecoder.decode"],
                "postconditions": ["decoder_handles_partial_streams"],
            },
            "executable_patch_plan": {
                "executable_plan_id": "executable_patch_plan_test",
                "status": "complete",
                "target_paths": [r"C:\Work\App\src\decoder.py"],
                "change_units": [
                    {
                        "target_file": r"C:\Work\App\src\decoder.py",
                        "target_symbol": "AdaptiveDecoder.decode",
                        "hunk_ids": ["hunk_1"],
                    }
                ],
                "rollback_strategy": {"strategy": "restore_previous_hunks"},
                "validation_steps": ["run_decoder_validation"],
            },
            "execution_preview": {
                "execution_preview_id": "execution_preview_test",
                "status": "complete",
                "target_paths": [r"C:\Work\App\src\decoder.py"],
                "change_summary": ["apply_patch_after_approval:C:\\Work\\App\\src\\decoder.py"],
            },
        },
        requested_actions=["apply_patch"],
        approval_required_for=["apply_patch"],
    )

    plan = ExecutablePlanService().validate_draft(draft)

    assert plan["valid"] is True
    assert plan["plan_kind"] == "executable_patch_plan"
    assert plan["executable_plan_ref"] == "executable_patch_plan_test"


def test_target_paths_include_execution_preview_chain():
    draft = _draft(
        draft_id="draft_patch_targets",
        contract_type="patch_request",
        operation_type="patch_request",
        runtime_profile="patch",
        intent_map={
            "risk": "medium",
            "context_ref": "test_context",
            "validation_plan": {"checks": ["patch_result", "validation_result"]},
            "rollback_plan": {"strategy": "restore_previous_hunks"},
            "execution_intent": {
                "workspace": r"C:\Work\App",
                "target_files": [r"C:\Work\App\src\decoder.py"],
            },
            "executable_patch_plan": {
                "target_paths": [r"C:\Work\App\src\decoder.py"],
                "change_units": [
                    {"target_file": r"C:\Work\App\src\metadata.py"},
                ],
            },
            "execution_preview": {
                "target_paths": [r"C:\Work\App\src\player.py"],
            },
        },
    )

    paths = ExecutablePlanService().real_target_paths(draft)

    assert r"C:\Work\App\src\decoder.py" in paths
    assert r"C:\Work\App\src\metadata.py" in paths
    assert r"C:\Work\App\src\player.py" in paths


def test_natural_approval_single_pending_applies_decision(tmp_path: Path):
    draft_store, preview_service, approvals = _stores(tmp_path)
    _create_real_approval(draft_store, preview_service, approvals, "approval_single")
    service = ChatApprovalCommandService(
        approvals=approvals,
        continuation=_Continuation({"status": "recorded", "reason_code": "approval_resume_disabled"}),
    )

    response = service.handle("chat_test", "pode implementar", source_channel="unit")

    assert response is not None
    assert response.approval_id == "approval_single"
    assert approvals.get_approval("approval_single").status == "approved"


def test_approve_task_run_id_zero_pending_returns_no_pending_for_task(tmp_path: Path):
    _, _, approvals = _stores(tmp_path)
    service = ChatApprovalCommandService(approvals=approvals, continuation=_Continuation({"status": "noop"}))

    response = service.handle("chat_test", "APROVAR task_run_missing", source_channel="unit")

    assert response is not None
    assert response.status == "blocked"
    assert response.contract_preview["reason_code"] == "no_pending_approval_for_task"
    assert "NENHUM_APPROVAL_PENDENTE" in response.contract_preview["message"]


def test_resume_blocked_reports_blocked_not_success(tmp_path: Path):
    draft_store, preview_service, approvals = _stores(tmp_path)
    _create_real_approval(draft_store, preview_service, approvals, "approval_blocked")
    service = ChatApprovalCommandService(
        approvals=approvals,
        continuation=_Continuation(
            {
                "status": "blocked",
                "task_run_id": "task_run_blocked",
                "block_reason_code": "project_generation_plan_missing",
                "files_written": False,
            }
        ),
    )

    response = service.handle("chat_test", "APROVAR approval_blocked", source_channel="unit")

    assert response is not None
    assert response.status == "blocked"
    assert "APPROVAL_REGISTERED_BUT_TASK_BLOCKED" in response.message
    assert "project_generation_plan_missing" in response.message


def test_resume_failed_reports_failed_not_blocked(tmp_path: Path):
    draft_store, preview_service, approvals = _stores(tmp_path)
    _create_real_approval(draft_store, preview_service, approvals, "approval_failed")
    service = ChatApprovalCommandService(
        approvals=approvals,
        continuation=_Continuation(
            {
                "status": "failed",
                "run_status": "failed",
                "run_id": "task_run_failed",
                "reason_code": "shell_exit_code_mismatch",
                "failed_step_id": "step_03_execute_governed_shell",
                "files_written": False,
            }
        ),
    )

    response = service.handle("chat_test", "APROVAR approval_failed", source_channel="unit")

    assert response is not None
    assert response.status == "failed"
    assert "APPROVAL_REGISTERED_BUT_TASK_FAILED" in response.message
    assert "APPROVAL_REGISTERED_BUT_TASK_BLOCKED" not in response.message
    assert "shell_exit_code_mismatch" in response.message
    assert "step_03_execute_governed_shell" in response.message
