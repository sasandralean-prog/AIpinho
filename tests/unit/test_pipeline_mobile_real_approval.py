from types import SimpleNamespace

from aipinho.services.mobile_view_models.pipeline_mobile_aggregator import PipelineMobileAggregator


class FakeApprovalService:
    def __init__(self, approval=None):
        self.approval = approval

    def list_approvals(self, **_filters):
        return [self.approval] if self.approval is not None else []

    def get_approval(self, approval_id):
        if self.approval is not None and self.approval.approval_id == approval_id:
            return self.approval
        return None


class FakeTaskRuntime:
    def __init__(self, approval_id=None, status="waiting_input"):
        self.approval_id = approval_id
        self.status = status

    def get_run(self, task_id):
        return SimpleNamespace(run_id=task_id, approval_id=self.approval_id, status=self.status) if self.approval_id else None

    def get_active_run(self):
        return SimpleNamespace(run_id="task_run_active", approval_id=self.approval_id, status=self.status) if self.approval_id else None


def pending_approval(*, run_id=None, task_id=None, approval_id="approval_test"):
    return SimpleNamespace(
        approval_id=approval_id,
        preview_id="preview_test",
        status="pending",
        actions_requested=["write_files"],
        run_id=run_id,
        task_id=task_id,
        operation_type="write_files",
        risk_level="medium",
        approval_scope="future_execution",
    )


def test_pipeline_exposes_real_pending_approval_without_latest_placeholder():
    view_model = PipelineMobileAggregator(
        approvals=FakeApprovalService(pending_approval(run_id="task_run_active")),
        task_runtime=FakeTaskRuntime(approval_id="approval_test"),
    ).view_model()

    card = next(card for card in view_model.cards if card.card_type == "approval")
    assert card.metadata["approval_id"] == "approval_test"
    assert card.metadata["preview_id"] == "preview_test"
    assert card.status == "pending"
    assert all(item.ref_id != "latest" for item in card.evidence)
    assert view_model.queue.requires_decision == 1
    assert view_model.selected_approval_id == "approval_test"
    assert view_model.approval_kind == "task_approval"
    assert view_model.linked_task_run_id == "task_run_active"
    assert view_model.queue.task_approvals_pending == 1
    assert view_model.queue.standalone_approvals_pending == 0


def test_pipeline_without_active_run_exposes_standalone_approval_separately():
    view_model = PipelineMobileAggregator(
        approvals=FakeApprovalService(pending_approval()),
        task_runtime=FakeTaskRuntime(),
    ).view_model()

    card = next(card for card in view_model.cards if card.card_type == "approval")
    assert card.metadata["approval_id"] == "approval_test"
    assert card.metadata["approval_kind"] == "future_execution"
    assert card.metadata["linked_task_run_id"] is None
    assert card.status == "pending"
    assert view_model.task_id is None
    assert view_model.selected_task_id is None
    assert view_model.selected_approval_id == "approval_test"
    assert view_model.linked_task_run_id is None
    assert view_model.queue.total == 0
    assert view_model.queue.task_approvals_pending == 0
    assert view_model.queue.standalone_approvals_pending == 1


def test_pipeline_explicit_terminal_run_does_not_become_active():
    view_model = PipelineMobileAggregator(
        approvals=FakeApprovalService(),
        task_runtime=FakeTaskRuntime(),
    ).view_model()

    task_card = next(card for card in view_model.cards if card.card_type == "task_state")
    assert task_card.status == "unknown"
    assert task_card.evidence == []
