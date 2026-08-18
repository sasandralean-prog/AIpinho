from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.services.chat.chat_service import ChatService
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
        summary = {"safe": step.step_type}
        if step.step_type == "run_role_pipeline":
            context.outputs["_role_pipeline"] = summary
        if step.step_type == "run_project_analysis":
            context.outputs["_project_analysis"] = summary
        return TaskStepOutcome(status="completed", summary=summary)


class RecordingResultPublisher:
    def __init__(self):
        self.calls = []

    def publish(self, run, result):
        self.calls.append((run, result))
        return {"status": "published"}


def test_service_creates_run_without_starting(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())

    assert run.status == "created"
    assert run.started_at is None
    assert run.task_id and run.task_id.startswith("task_")
    assert run.operation_id and run.operation_id.startswith("op_")
    assert run.task_run_id == run.run_id
    assert run.bootstrap_context["task_id"] == run.task_id
    assert run.warnings == []
    event_types = [event.type for event in task_runtime_service.get_events(run.run_id)]
    assert "run_created" in event_types
    assert "ExecutionPlanCreated" in event_types


def test_service_creates_canonical_execution_plan_for_every_run(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())

    plan = run.plan.canonical_execution_plan
    assert plan is not None
    assert plan.execution_id.startswith("execution_")
    assert plan.task_id == run.task_id
    assert plan.taskrun_id == run.run_id
    assert plan.operation_kind == run.operation_type
    assert plan.required_capabilities == run.capabilities_required
    assert run.plan.metadata["execution_id"] == plan.execution_id
    assert run.plan.candidate_plan is not None


def test_service_materializes_execution_graph_for_every_run(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())

    graph = run.execution_graph
    assert graph is not None
    assert graph.run_id == run.run_id
    assert graph.context.contract_type == run.contract_type
    assert len(graph.nodes) == len(run.plan.steps)
    assert all(node.node_id.startswith("node_") for node in graph.nodes)
    assert all(node.worker for node in graph.nodes)
    assert all("worker_route" in node.validation_gate for node in graph.nodes)
    assert graph.checkpoints
    assert task_runtime_service.get_execution_graph(run.run_id).graph_id == graph.graph_id


def test_execution_graph_tracks_completed_runtime_nodes(task_runtime_service):
    task_runtime_service.loop.executor = CompletingExecutor()
    run = task_runtime_service.create_run(runtime_request(start_immediately=True))

    result = task_runtime_service.process_queue()
    completed = task_runtime_service.get_run(run.run_id)

    assert result["status"] == "completed"
    assert completed.execution_graph is not None
    assert completed.execution_graph.status == "completed"
    assert completed.execution_graph.lifecycle.completed_node_ids
    assert all(node.status == "completed" for node in completed.execution_graph.nodes)


def test_operational_memory_is_recorded_for_created_task_run(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())

    records = task_runtime_service.get_operational_memory(run.run_id)

    assert {record.memory_type for record in records} >= {"decision", "strategy", "execution"}
    assert all(record.source_type == "task_run" for record in records)
    assert all(record.source_run_id == run.run_id for record in records)
    assert all("operational" in record.tags for record in records)


def test_operational_memory_records_completion_without_curated_memory_mutation(task_runtime_service):
    task_runtime_service.loop.executor = CompletingExecutor()
    run = task_runtime_service.create_run(runtime_request(start_immediately=True))

    task_runtime_service.process_queue()
    records = task_runtime_service.get_operational_memory(run.run_id)

    assert any(record.memory_type == "learning" for record in records)
    assert any(record.outcome == "completed" for record in records)
    assert all(not record.memory_id.startswith("learning_memory_") for record in records)
    assert all(record.source_type == "task_run" for record in records)


def test_operational_memory_records_failure_and_recovery(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request(policy={}))

    records = task_runtime_service.get_operational_memory(run.run_id)

    assert run.status == "blocked"
    assert any(record.memory_type == "failure" for record in records)
    assert any(record.memory_type == "recovery" for record in records)
    assert all(record.outcome == "blocked" for record in records)


def test_service_queues_explicit_auto_run_request(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request(start_immediately=True))

    assert run.status == "queued"
    assert run.auto_run_requested is True
    assert "start_immediately_ignored_explicit_start_required" not in run.warnings
    assert task_runtime_service.get_result(run.run_id) is None


def test_service_processes_only_governed_auto_run_queue_head(task_runtime_service):
    task_runtime_service.loop.executor = CompletingExecutor()
    run = task_runtime_service.create_run(runtime_request(start_immediately=True))

    result = task_runtime_service.process_queue()

    assert result["started_run_id"] == run.run_id
    assert result["status"] == "completed"
    assert task_runtime_service.get_run(run.run_id).status == "completed"


def test_service_publishes_terminal_result_after_manual_start(task_runtime_store, tmp_path):
    publisher = RecordingResultPublisher()
    runtime = TaskRuntimeService(
        store=task_runtime_store,
        result_publisher=publisher,
        operational_memory=OperationalMemoryService(root=tmp_path / "operational_memory"),
    )
    runtime.loop.executor = CompletingExecutor()
    run = runtime.create_run(runtime_request())

    completed, result = runtime.start(run.run_id)

    assert completed.status == "completed"
    assert result.status == "completed"
    assert publisher.calls == [(completed, result)]


def test_service_blocks_missing_policy_decision(task_runtime_service):
    request = runtime_request(policy={})
    run = task_runtime_service.create_run(request)

    assert run.status == "blocked"
    assert "missing_policy_decision" in run.blocked_reasons
    assert run.block_cause is not None
    assert run.block_cause.block_reason_code == "missing_policy_decision"
    assert run.block_cause.trace_id
    assert any(event.type == "task_blocked" for event in task_runtime_service.get_events(run.run_id))


def test_service_waits_for_approval_when_policy_requires_apply_patch(task_runtime_store, tmp_path):
    approval_id = "approval_pending_for_apply_patch"
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
            reason="test_policy_requires_approval",
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
    request = runtime_request(
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

    run = runtime.create_run(request)

    assert run.status == "waiting_input"
    assert run.approval_id == approval_id
    linked = runtime.approvals.get_approval(approval_id)
    assert linked is not None
    assert linked.run_id == run.run_id
    assert linked.task_id == run.task_id
    assert linked.execution_id == run.plan.canonical_execution_plan.execution_id
    assert linked.execution_plan_snapshot["execution_id"] == run.plan.canonical_execution_plan.execution_id
    assert run.blocked_reasons == []
    assert "action_not_granted_by_policy:apply_patch" not in run.blocked_reasons
    assert any(event.type == "approval_required" for event in runtime.get_events(run.run_id))
    assert any("approval_required" in item.data.get("blocked_reasons", []) for item in run.trace)


def test_service_status_reflects_governed_runtime_capabilities(task_runtime_service):
    status = task_runtime_service.status()

    assert status.enabled is True
    assert status.mode == "governed_controlled"
    assert status.write_enabled is True
    assert status.patch_enabled is True
    assert status.shell_enabled is True
    assert status.background_execution is True


def test_chat_suggests_task_run_but_never_executes_it(task_runtime_store, tmp_path):
    runtime = TaskRuntimeService(
        store=task_runtime_store,
        operational_memory=OperationalMemoryService(root=tmp_path / "operational_memory"),
    )
    chat = ChatService(task_runtime_service=runtime)

    response = chat.respond(TaskRunRequest.__pydantic_validator__) if False else chat.respond(
        __import__("aipinho.schemas.chat.chat_request", fromlist=["ChatRequest"]).ChatRequest(
            message="Resuma este projeto sem alterar arquivos.",
            context={"active_workspace": None, "surface": "api"},
        )
    )

    assert response.status in {"ok", "preview", "needs_clarification", "blocked", "degraded"}
    assert runtime.list_runs() == []
