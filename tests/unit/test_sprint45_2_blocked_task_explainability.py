from types import SimpleNamespace

from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.runtime.task_block_cause import TaskBlockCause
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft, TaskDraftWorkspace
from aipinho.schemas.tasks.task_preview import TaskPreview
from aipinho.services.mobile_view_models.pipeline_mobile_aggregator import PipelineMobileAggregator
from aipinho.services.runtime.task_block_cause_service import TaskBlockCauseService
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from aipinho.services.runtime.task_queue_service import TaskQueueService
from aipinho.services.runtime.task_run_lifecycle_service import TaskRunLifecycleService
from tests.support.runtime_fixtures import one_step_plan


class NullRegressionCandidates:
    def create_for_failure(self, **_kwargs):
        return None


def test_block_cause_maps_source_read_policy_without_sensitive_content():
    run = TaskRun(
        run_id="task_run_bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        source_type="preview",
        contract_type="readonly_analysis",
        requested_actions=["read_files"],
        workspace="X:/authorized/workspace",
        policy_snapshot={"status": "allowed"},
        plan=one_step_plan(action="read_files"),
    )
    cause = TaskBlockCauseService(regression_candidates=NullRegressionCandidates()).build(
        run,
        ["sandbox_readonly_disabled"],
    )

    assert cause.blocked_stage == "source_read_policy"
    assert cause.block_reason_code == "sandbox_readonly_disabled"
    assert cause.source_read_status == "blocked"
    assert cause.artifact_output_status == "not_created"
    assert cause.safe_alternatives
    assert cause.trace_id


def test_approval_required_preview_creates_pending_approval(monkeypatch, task_runtime_store):
    snapshot = ApprovalPolicySnapshot(
        policy_status="allowed",
        allowed_actions=["read_files"],
        approval_required_for=["read_files"],
        workspace_status="allowed",
        trace_hash="trace-hash",
    )
    preview = TaskPreview(
        preview_id="preview_test",
        draft_id="draft_test",
        session_id="session_test",
        status="approval_required",
        contract_type="in_chat_final_report",
        requested_actions=["read_files"],
        allowed_actions=["read_files"],
        approval_required_for=["read_files"],
        policy_snapshot=snapshot,
        created_at="2026-06-11T00:00:00+00:00",
        updated_at="2026-06-11T00:00:00+00:00",
    )
    draft = TaskContractDraft(
        draft_id="draft_test",
        session_id="session_test",
        contract_type="in_chat_final_report",
        workspace=TaskDraftWorkspace(status="not_required"),
        requested_actions=["read_files"],
        intent_map={"intent_type": "readonly_analysis"},
        policy_decision={"status": "allowed"},
        created_at="2026-06-11T00:00:00+00:00",
        updated_at="2026-06-11T00:00:00+00:00",
    )
    approval = SimpleNamespace(approval_id="approval_generated")
    runtime = TaskRuntimeService(store=task_runtime_store)
    runtime.previews = SimpleNamespace(get_preview=lambda _preview_id: preview)
    runtime.drafts = SimpleNamespace(get_draft=lambda _draft_id: draft)
    runtime.approvals = SimpleNamespace(
        create_approval_for_preview=lambda *_args, **_kwargs: approval,
    )
    captured = {}
    monkeypatch.setattr(runtime, "create_run", lambda request: captured.setdefault("request", request))

    request = runtime.create_from_preview(preview.preview_id)

    assert request.approval_id == "approval_generated"


class FakeRuntime:
    def __init__(self, run):
        self.run = run
        self.lifecycle = SimpleNamespace(is_terminal=lambda _status: True)

    def queue_status(self):
        raise RuntimeError("no queue fixture")

    def get_run(self, _task_id):
        return self.run

    def get_active_run(self):
        return None


class NoApproval:
    def get_approval(self, _approval_id):
        return None


def test_mobile_blocked_task_is_not_rendered_safe():
    cause = TaskBlockCause(
        block_id="block_test",
        task_id="task_run_cccccccccccccccccccccccccccccccc",
        blocked_stage="workspace_resolution",
        block_reason_code="forbidden_root",
        human_reason="Workspace blocked.",
        technical_reason_sanitized="forbidden_root",
        safe_alternatives=["Choose an authorized workspace."],
    )
    run = TaskRun(
        run_id=cause.task_id,
        source_type="preview",
        status="blocked",
        contract_type="readonly_analysis",
        policy_snapshot={"status": "blocked"},
        plan=one_step_plan(),
        block_cause=cause,
    )

    view = PipelineMobileAggregator(
        approvals=NoApproval(),
        task_runtime=FakeRuntime(run),
    ).view_model(run.run_id)

    task_card = next(card for card in view.cards if card.card_type == "task_state")
    assert task_card.answers.is_it_safe.answer == "blocked"
    assert "workspace resolution" in task_card.answers.is_it_safe.reason
    assert task_card.metadata["block_reason_code"] == "forbidden_root"


class RejectedApprovalService:
    def get_approval(self, _approval_id):
        return SimpleNamespace(status="rejected")


def test_rejected_approval_becomes_structured_block(task_runtime_store):
    run = TaskRun(
        run_id="task_run_dddddddddddddddddddddddddddddddd",
        source_type="preview",
        status="waiting_input",
        approval_id="approval_rejected",
        contract_type="in_chat_final_report",
        policy_snapshot={"status": "allowed", "approval_required_for": ["read_files"]},
        requested_actions=["read_files"],
        plan=one_step_plan(action="read_files"),
    )
    task_runtime_store.create_run(run)
    queue = TaskQueueService(
        store=task_runtime_store,
        lifecycle=TaskRunLifecycleService(),
        approvals=RejectedApprovalService(),
    )

    queue.reconcile()
    updated = task_runtime_store.get_run(run.run_id)

    assert updated is not None
    assert updated.status == "blocked"
    assert updated.block_cause is not None
    assert updated.block_cause.blocked_stage == "approval_denied"
    assert updated.block_cause.approval_status == "denied"
    assert any(event.type == "approval_denied" for event in task_runtime_store.get_events(run.run_id))
