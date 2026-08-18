from __future__ import annotations

from pathlib import Path

from aipinho.schemas.intent.intent_map import IntentMap, IntentSummary
from aipinho.schemas.policy.effective_policy import EffectivePolicy
from aipinho.schemas.policy.policy_decision import PolicyDecision, PolicyResolveRequest, RoleInput, WorkspaceInput
from aipinho.schemas.tasks.task_contract import TaskContractInput
from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft, TaskDraftWorkspace
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.approvals.approval_task_continuation_service import ApprovalTaskContinuationService
from aipinho.services.config_governance.workspace_permission_matrix_service import WorkspacePermissionMatrixService
from aipinho.services.governance.operation_contract_service import OperationContractService
from aipinho.services.orchestration.task_contract_draft_service import TaskContractDraftService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.orchestration.task_preview_store import TaskPreviewStore
from aipinho.services.policy_kernel.policy_kernel_service import PolicyKernelService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.speaker.speaker_service import SpeakerService
from aipinho.services.session.session_store import utc_now


TARGET_MUTABLE_WORKSPACE = r"C:\Users\rafae\Documents\AIpinhoTestes\Sprint-File-Sync-main"


def _policy_request(actions: list[str], *, workspace: str = TARGET_MUTABLE_WORKSPACE, read_only: bool = False) -> PolicyResolveRequest:
    return PolicyResolveRequest(
        intent=IntentSummary(
            intent_type="patch_request",
            requires_task=True,
            requires_workspace=True,
            confidence=1.0,
        ),
        task=TaskContractInput(
            task_type="patch_request",
            requested_actions=actions,
            read_only=read_only,
        ),
        workspace=WorkspaceInput(path=workspace, declared=True),
        role=RoleInput(role_id="executor"),
    )


def test_policy_ask_apply_patch_creates_approval() -> None:
    decision = PolicyKernelService().resolve(_policy_request(["apply_patch"]))

    assert decision.status == "needs_approval"
    assert decision.approval_required_for == ["apply_patch"]
    assert "apply_patch" not in decision.denied_actions
    assert decision.safe_to_preview is True
    assert decision.safe_to_execute is False


def test_policy_ask_write_files_creates_approval() -> None:
    decision = PolicyKernelService().resolve(_policy_request(["write_files"]))

    assert decision.status == "needs_approval"
    assert decision.approval_required_for == ["write_files"]
    assert "write_files" not in decision.denied_actions
    assert decision.safe_to_preview is True
    assert decision.safe_to_execute is False


def test_policy_denied_apply_patch_blocks_with_reason(tmp_path: Path) -> None:
    forbidden = tmp_path / "readonly"
    forbidden.mkdir()
    registry = tmp_path / "workspace_registry.yaml"
    registry.write_text(
        f"""
schema_version: 1
workspaces:
  - workspace_id: readonly
    root_path: {forbidden}
    role: source_readonly
""",
        encoding="utf-8",
    )
    matrix = WorkspacePermissionMatrixService(registry).load()
    contract = OperationContractService(permission_matrix=matrix).build(
        source_channel="chat",
        session_id="chat_test",
        user_text="Aplique um patch.",
        intent_type="patch_request",
        operation_type="patch_request",
        requested_actions=["apply_patch"],
        workspace_refs=[str(forbidden)],
        target_paths=[str(forbidden)],
    )

    assert contract.approval_required is False
    assert contract.permission_decisions[0].decision == "denied"
    assert contract.permission_decisions[0].reason_code == "permission_denied"


def test_create_approval_request_does_not_require_write_permission() -> None:
    decision = PolicyKernelService().resolve(_policy_request(["write_files", "apply_patch"]))

    assert decision.status == "needs_approval"
    assert set(decision.approval_required_for) == {"write_files", "apply_patch"}
    assert decision.denied_actions == []
    assert decision.safe_to_preview is True


def test_approve_text_resumes_write_operation_by_creating_task_run(tmp_path: Path) -> None:
    draft_store = TaskDraftStore(tmp_path / "drafts")
    preview_service = TaskPreviewService(
        store=TaskPreviewStore(tmp_path / "previews"),
        draft_store=draft_store,
    )
    approval_service = ApprovalService(
        store=ApprovalStore(tmp_path / "approvals"),
        preview_service=preview_service,
        draft_store=draft_store,
    )
    now = utc_now()
    draft = TaskContractDraft(
        draft_id="draft_write_resume",
        session_id="chat_write_resume",
        status="approval_required",
        intent_map={
            "prompt": "Crie um arquivo reports/kernel_policy_smoke_test.md com o texto teste.",
            "raw_prompt": "Crie um arquivo reports/kernel_policy_smoke_test.md com o texto teste.",
            "intent": "governed_file_write",
            "risk": "medium",
            "target_path": "reports/kernel_policy_smoke_test.md",
            "context_ref": "unit_write_context",
            "validation_plan": {"checks": ["filesystem_operation_recorded"]},
            "rollback_plan": {"strategy": "delete_created_test_file"},
        },
        policy_decision={
            "decision_id": "policy_write_resume",
            "status": "needs_approval",
            "allowed_actions": [],
            "denied_actions": [],
            "approval_required_for": ["write_files"],
        },
        contract_type="filesystem_write",
        operation_type="filesystem_write_file",
        intent_type="governed_file_write",
        runtime_profile="write_file",
        capabilities_required=["write_workspace"],
        source_scope="unit_test",
        requires_workspace=True,
        workspace=TaskDraftWorkspace(path=TARGET_MUTABLE_WORKSPACE, status="confirmed"),
        requested_actions=["write_files"],
        approval_required_for=["write_files"],
        expected_outcomes=["filesystem_operation", "validation_result"],
        safe_to_preview=True,
        safe_to_execute=False,
        created_at=now,
        updated_at=now,
    )
    draft_store.save(draft)
    preview = preview_service.create_preview_from_draft(draft.draft_id)
    assert preview is not None
    approval = approval_service.create_approval_for_preview(preview.preview_id, actions=["write_files"], reason="unit_test")
    _decision, approved = approval_service.approve(approval.approval_id, reason="unit_test")
    run_store = TaskRunStore(tmp_path / "runs")

    result = ApprovalTaskContinuationService(
        approvals=approval_service,
        store=run_store,
    ).after_decision(approved, auto_process=False)

    assert result["status"] == "ok"
    assert result["resumed"] is True
    assert result["result_code"] == "task_run_created_from_approved_preview"
    assert "reason_code" not in result
    assert result["run_id"].startswith("task_run_")
    run = run_store.get_run(result["run_id"])
    assert run is not None
    assert run.approval_id == approval.approval_id
    assert run.requested_actions == ["write_files"]


def test_runtime_session_grants_dir_is_writable_by_runtime_policy() -> None:
    matrix = WorkspacePermissionMatrixService().load()
    runtime_path = r"C:\Dev\AIpinho\data\runtime\session_grants"

    create_decision = matrix.decide(path=runtime_path, permission="create_file")
    modify_decision = matrix.decide(path=runtime_path, permission="modify_file")
    patch_decision = matrix.decide(path=runtime_path, permission="apply_patch")

    assert create_decision.status == "allowed"
    assert modify_decision.status == "allowed"
    assert patch_decision.status == "denied"
    assert create_decision.workspace_id == "aipinho_runtime"


def test_blocked_message_not_contradictory() -> None:
    intent = IntentMap(
        intent_id="intent_test",
        raw_prompt="Crie arquivo",
        normalized_prompt="crie arquivo",
        intent_type="filesystem_write_request",
        requires_task=True,
        requires_workspace=True,
    )
    policy = PolicyDecision(
        decision_id="policy_test",
        status="allowed",
        contract_type="filesystem_write",
        denied_actions=["write_files"],
        effective_policy=EffectivePolicy(denied_actions=["write_files"]),
    )

    message = SpeakerService().compose_blocked(intent, policy)

    assert "Pedido bloqueado: bloqueado pela Policy Kernel" in message
    assert "Pedido bloqueado: permitido pela Policy Kernel" not in message
