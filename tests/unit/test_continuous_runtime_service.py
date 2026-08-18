from datetime import datetime, timedelta, timezone

from aipinho.core.paths import PATHS
from aipinho.schemas.approvals.approval_policy_snapshot import ApprovalPolicySnapshot
from aipinho.schemas.approvals.approval_request import ApprovalRequest
from aipinho.schemas.common.actor import Actor
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
from aipinho.services.memory.operational_memory_service import OperationalMemoryService
from aipinho.services.runtime.readonly_task_step_runner import TaskStepOutcome
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from tests.support.runtime_fixtures import allowed_policy, runtime_request


class CompletingExecutor:
    def execute_step(self, run, step, context):
        return TaskStepOutcome(status="completed", summary={"step": step.step_id})


def test_continuous_runtime_continues_created_run(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())

    cycle = task_runtime_service.evaluate_continuous_runtime(run.run_id)

    assert cycle.status == "continue"
    assert cycle.current_stage == "continuation"
    assert cycle.next_action == "continue_runtime"
    assert cycle.checkpoints


def test_continuous_runtime_completes_with_evidence(task_runtime_service):
    task_runtime_service.loop.executor = CompletingExecutor()
    run = task_runtime_service.create_run(runtime_request(start_immediately=True))

    task_runtime_service.process_queue()
    cycle = task_runtime_service.evaluate_continuous_runtime(run.run_id)

    assert cycle.status == "completed"
    assert cycle.current_stage == "conclusion"
    assert cycle.reason_code == "evidence_backed_completion"


def test_continuous_runtime_waits_for_approval(task_runtime_store, tmp_path):
    approval_id = "approval_continuous_runtime"
    approval_store = ApprovalStore(root=tmp_path / "approvals")
    now = datetime.now(timezone.utc)
    approval_store.save(
        ApprovalRequest(
            approval_id=approval_id,
            preview_id="preview_patch_request",
            draft_id="draft_patch_request",
            session_id="session_test",
            status="pending",
            actions_requested=["apply_patch"],
            approval_scope="future_execution",
            reason="test_continuous_runtime_approval",
            risk_level="medium",
            policy_snapshot=ApprovalPolicySnapshot(
                policy_status="needs_approval",
                allowed_actions=["patch_preview"],
                approval_required_for=["apply_patch"],
                workspace_status="allowed",
                risk_level="medium",
                trace_hash="test_trace_hash",
            ),
            expires_at=(now + timedelta(minutes=30)).isoformat(),
            created_at=now.isoformat(),
            updated_at=now.isoformat(),
            created_by=Actor(type="system", id="test"),
        )
    )
    runtime = TaskRuntimeService(
        store=task_runtime_store,
        approvals=ApprovalService(store=approval_store),
        operational_memory=OperationalMemoryService(root=tmp_path / "operational_memory"),
    )
    run = runtime.create_run(
        runtime_request(
            workspace=str(PATHS.project_root),
            contract_type="patch_request",
            operation_type="patch_preview",
            runtime_profile="patch",
            actions=["patch_preview", "apply_patch"],
            approval_id=approval_id,
            policy=allowed_policy(
                status="needs_approval",
                contract_type="patch_request",
                allowed_actions=["patch_preview"],
                approval_required_for=["apply_patch"],
                safe_to_preview=True,
                safe_to_execute=False,
            ),
        )
    )

    cycle = runtime.evaluate_continuous_runtime(run.run_id)

    assert cycle.status == "needs_approval"
    assert cycle.approval_id == approval_id
    assert cycle.next_action == "wait_for_approval"


def test_continuous_runtime_blocks_real_block(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request(policy={}))

    cycle = task_runtime_service.evaluate_continuous_runtime(run.run_id)

    assert cycle.status == "blocked"
    assert cycle.next_action == "surface_block_reason"
    assert cycle.reason_code == "missing_policy_decision"
