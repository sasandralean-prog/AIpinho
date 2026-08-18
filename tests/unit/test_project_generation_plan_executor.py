from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.approvals.approval_store import ApprovalStore
import aipinho.services.runtime.task_runtime_service as task_runtime_module
import aipinho.services.runtime.task_run_guard as task_run_guard_module
from aipinho.schemas.runtime.task_run import TaskRun
from aipinho.schemas.runtime.task_run_context import TaskRunContext
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.schemas.tasks.task_contract_draft import TaskContractDraft, TaskDraftWorkspace
from aipinho.services.orchestration.task_contract_draft_service import TaskContractDraftService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.orchestration.task_preview_store import TaskPreviewStore
from aipinho.services.runtime.governed_task_step_runner import GovernedTaskStepRunner
from aipinho.services.runtime.project_generation_plan_executor import ProjectGenerationPlanExecutor
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService


def _run(workspace: Path, plan: dict) -> TaskRun:
    return TaskRun(
        run_id="task_run_aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        source_type="preview",
        session_id="chat_test",
        workspace=str(workspace),
        contract_type="project_generation",
        operation_type="project_generation",
        runtime_profile="project_generation",
        requested_actions=["write_files"],
        capabilities_required=["write_workspace"],
        intent_map={"project_generation_plan": plan},
        mode="governed",
        policy_snapshot={"status": "ask", "approval_required_for": ["write_files"]},
        approval_id="approval_test",
        plan=TaskRunPlan(
            plan_id="plan_test",
            contract_type="project_generation",
            steps=[
                TaskRunStep(
                    step_id="step_01_execute_project_generation",
                    step_type="execute_project_generation",
                    action="write_files",
                    side_effect=True,
                ),
                TaskRunStep(
                    step_id="step_02_validate_project_result",
                    step_type="validate_project_result",
                    action="validate_runtime",
                    side_effect=False,
                ),
            ],
        ),
    )


def test_project_generation_plan_executor_creates_files(tmp_path: Path):
    workspace = tmp_path / "App"
    plan = {
        "target_workspace": str(workspace),
        "directories_to_create": [{"path": "src"}],
        "files_to_create": [
            {"path": "index.html", "content": "<h1>App</h1>"},
            {"path": "src/app.js", "content": "console.log('ok');"},
        ],
        "validation_steps": ["file_exists"],
        "expected_outputs": ["index.html", "src/app.js"],
    }

    result = ProjectGenerationPlanExecutor().execute(_run(workspace, plan))

    assert result is not None
    assert result["status"] == "succeeded"
    assert (workspace / "index.html").read_text(encoding="utf-8") == "<h1>App</h1>"
    assert (workspace / "src" / "app.js").read_text(encoding="utf-8") == "console.log('ok');"


def test_project_generation_plan_executor_blocks_path_escape(tmp_path: Path):
    workspace = tmp_path / "App"
    outside = tmp_path / "outside.txt"
    plan = {
        "target_workspace": str(workspace),
        "files_to_create": [{"path": str(outside), "content": "no"}],
        "validation_steps": ["file_exists"],
        "expected_outputs": ["outside.txt"],
    }

    result = ProjectGenerationPlanExecutor().execute(_run(workspace, plan))

    assert result is not None
    assert result["status"] == "blocked"
    assert result["reason_code"] == "target_path_outside_workspace"
    assert not outside.exists()


def test_governed_runner_uses_project_generation_plan(tmp_path: Path):
    workspace = tmp_path / "App"
    plan = {
        "target_workspace": str(workspace),
        "files_to_create": [{"path": "README.md", "content": "# App\n"}],
        "validation_steps": ["file_exists"],
        "expected_outputs": ["README.md"],
    }
    run = _run(workspace, plan)
    context = TaskRunContext(run_id=run.run_id, workspace=str(workspace))
    runner = GovernedTaskStepRunner()

    outcome = runner._execute_project_generation(run, context)
    validation = runner._validate_project_result(run, context)

    assert outcome.status == "completed"
    assert context.outputs["_project_generation"]["status"] == "succeeded"
    assert context.outputs["_validation_result"]["status"] == "passed"
    assert validation.status == "completed"
    assert validation.summary["validated_output"] == "project_generation"
    assert (workspace / "README.md").read_text(encoding="utf-8") == "# App\n"


def _shell_run(workspace: Path, shell_plan: dict) -> TaskRun:
    run = _run(workspace, {})
    run.contract_type = "governed_shell_request"
    run.operation_type = "run_command"
    run.runtime_profile = "shell_build_test"
    run.requested_actions = ["run_command"]
    run.capabilities_required = ["shell"]
    run.intent_map = {"shell_plan": shell_plan}
    return run


class _FakeShellGateway:
    def __init__(self, exit_code: int) -> None:
        self.exit_code = exit_code
        self.last_request = None

    def invoke(self, *_args, **_kwargs):
        self.last_request = _args[-1] if _args else None
        return SimpleNamespace(
            status="succeeded",
            tool_invocation=SimpleNamespace(tool_invocation_id="tool_shell_1", error_code=None, block_reason_code=None),
            policy_decision=SimpleNamespace(decision="allow", reason_code="test_shell_allowed"),
            output={"exit_code": self.exit_code, "stdout_sanitized": "ok", "stderr_sanitized": "", "duration_ms": 1},
            validation_result=None,
            artifacts=[],
        )


class _FakeShellActions:
    def __init__(self, exit_code: int) -> None:
        self.tool_gateway = _FakeShellGateway(exit_code)

    def infer_workspace_id(self, workspace_context: str) -> str:
        return f"workspace:{workspace_context}"


def test_governed_runner_executes_shell_plan(tmp_path: Path):
    workspace = tmp_path / "App"
    workspace.mkdir()
    runner = GovernedTaskStepRunner(local_actions=_FakeShellActions(exit_code=0))
    runner._agent_run_id = lambda _run, _operation_type: "agent_run_shell"
    context = TaskRunContext(run_id="task_run_shell", workspace=str(workspace))

    outcome = runner._execute_governed_shell(
        _shell_run(
            workspace,
            {"command": "gradle assembleDebug", "cwd": str(workspace), "shell_category": "build_shell", "expected_exit_code": 0},
        ),
        context,
    )
    validation = runner._validate_shell_result(_shell_run(workspace, {}), context)

    assert outcome.status == "completed"
    assert context.outputs["_shell"]["output"]["exit_code"] == 0
    assert runner.local_actions.tool_gateway.last_request.input["cwd"] == str(workspace)
    assert validation.status == "completed"


def test_governed_runner_shell_nonzero_exit_does_not_validate(tmp_path: Path):
    workspace = tmp_path / "App"
    workspace.mkdir()
    runner = GovernedTaskStepRunner(local_actions=_FakeShellActions(exit_code=1))
    runner._agent_run_id = lambda _run, _operation_type: "agent_run_shell"
    context = TaskRunContext(run_id="task_run_shell", workspace=str(workspace))

    outcome = runner._execute_governed_shell(
        _shell_run(
            workspace,
            {"command": "gradle assembleDebug", "cwd": str(workspace), "shell_category": "build_shell", "expected_exit_code": 0},
        ),
        context,
    )
    validation = runner._validate_shell_result(_shell_run(workspace, {}), context)

    assert outcome.status == "failed"
    assert "shell_exit_code_mismatch" in outcome.violations
    assert context.outputs["_shell"]["status"] == "failed"
    assert validation.status == "blocked"


def test_project_generation_executor_loads_unsanitized_draft_plan(tmp_path: Path):
    workspace = tmp_path / "App"
    draft_store = TaskDraftStore(tmp_path / "drafts")
    draft_store.save(
        TaskContractDraft(
            draft_id="draft_with_full_plan",
            session_id="chat_test",
            status="approved_for_future_execution",
            intent_map={
                "project_generation_plan": {
                    "target_workspace": str(workspace),
                    "files_to_create": [{"path": "index.html", "content": "<h1>Real</h1>"}],
                    "validation_steps": ["file_exists"],
                    "expected_outputs": ["index.html"],
                }
            },
            contract_type="project_generation",
            operation_type="project_generation",
            runtime_profile="project_generation",
            workspace=TaskDraftWorkspace(path=str(workspace), status="confirmed"),
            requested_actions=["write_files"],
            expected_outcomes=["project_generation", "validation_result"],
            created_at="now",
            updated_at="now",
        )
    )
    run = _run(
        workspace,
        {
            "target_workspace": str(workspace),
            "files_to_create": [{"path": "index.html", "content": "[omitted_by_task_run_store]"}],
        },
    )
    run.draft_id = "draft_with_full_plan"

    result = ProjectGenerationPlanExecutor(draft_store=draft_store).execute(run)

    assert result is not None
    assert result["status"] == "succeeded"
    assert (workspace / "index.html").read_text(encoding="utf-8") == "<h1>Real</h1>"


def test_no_executor_reads_sanitized_taskrun_content(tmp_path: Path):
    workspace = tmp_path / "App"
    draft_store = TaskDraftStore(tmp_path / "drafts")
    draft_store.save(
        TaskContractDraft(
            draft_id="draft_full_source",
            session_id="chat_test",
            status="approved_for_future_execution",
            intent_map={
                "project_generation_plan": {
                    "target_workspace": str(workspace),
                    "files_to_create": [{"path": "app.txt", "content": "full approved content"}],
                    "validation_steps": ["file_exists"],
                    "expected_outputs": ["app.txt"],
                }
            },
            contract_type="project_generation",
            operation_type="project_generation",
            runtime_profile="project_generation",
            workspace=TaskDraftWorkspace(path=str(workspace), status="confirmed"),
            requested_actions=["write_files"],
            expected_outcomes=["project_generation", "validation_result"],
            created_at="now",
            updated_at="now",
        )
    )
    run = _run(
        workspace,
        {
            "target_workspace": str(workspace),
            "files_to_create": [{"path": "app.txt", "content": "[omitted_by_task_run_store]"}],
        },
    )
    run.draft_id = "draft_full_source"

    result = ProjectGenerationPlanExecutor(draft_store=draft_store).execute(run)

    assert result is not None
    assert result["status"] == "succeeded"
    assert (workspace / "app.txt").read_text(encoding="utf-8") == "full approved content"


def test_omitted_placeholder_never_written(tmp_path: Path):
    workspace = tmp_path / "App"
    plan = {
        "target_workspace": str(workspace),
        "files_to_create": [{"path": "app.txt", "content": "[omitted_by_task_run_store]"}],
    }

    result = ProjectGenerationPlanExecutor(draft_store=TaskDraftStore(tmp_path / "drafts")).execute(
        _run(workspace, plan)
    )

    assert result is not None
    assert result["status"] == "blocked"
    assert result["reason_code"] == "file_content_omitted_by_sanitization"
    assert not (workspace / "app.txt").exists()


def test_taskdraft_is_executable_source_for_project_generation(tmp_path: Path):
    workspace = tmp_path / "App"
    draft_store = TaskDraftStore(tmp_path / "drafts")
    draft_store.save(
        TaskContractDraft(
            draft_id="draft_source_of_truth",
            session_id="chat_test",
            status="approved_for_future_execution",
            intent_map={
                "project_generation_plan": {
                    "target_workspace": str(workspace),
                    "files_to_create": [{"path": "source.txt", "content": "from taskdraft"}],
                }
            },
            contract_type="project_generation",
            operation_type="project_generation",
            runtime_profile="project_generation",
            workspace=TaskDraftWorkspace(path=str(workspace), status="confirmed"),
            requested_actions=["write_files"],
            expected_outcomes=["project_generation", "validation_result"],
            created_at="now",
            updated_at="now",
        )
    )
    run = _run(workspace, {"target_workspace": str(workspace), "files_to_create": []})
    run.draft_id = "draft_source_of_truth"

    result = ProjectGenerationPlanExecutor(draft_store=draft_store).execute(run)

    assert result is not None
    assert result["status"] == "succeeded"
    assert (workspace / "source.txt").read_text(encoding="utf-8") == "from taskdraft"


def test_taskrun_is_safe_display_source_only(tmp_path: Path):
    workspace = tmp_path / "App"
    plan = {
        "target_workspace": str(workspace),
        "files_to_create": [{"path": "display.txt", "content": "[omitted_by_task_run_store]"}],
    }
    run = _run(workspace, plan)

    result = ProjectGenerationPlanExecutor().execute(run)

    assert result is not None
    assert result["status"] == "blocked"
    assert result["reason_code"] == "file_content_omitted_by_sanitization"


def test_taskruntime_uses_custom_taskdraft_store_as_execution_source(tmp_path: Path, monkeypatch):
    class FakeWorkspacePolicy:
        def load(self):
            return self

        def evaluate(self, workspace_path, requires_workspace=True):
            return SimpleNamespace(
                status="allowed",
                workspace_path=workspace_path,
                blocked=False,
                needs_clarification=False,
                reason="test_workspace_allowed",
            )

    class FakeWorkspaceRoleContracts:
        def load(self):
            return self

        def resolve(self, workspace_path, required=True):
            return SimpleNamespace(
                status="allowed",
                reason="workspace_allowed",
                contract=SimpleNamespace(role="target_mutable"),
            )

    class FakePermissionMatrix:
        def load(self):
            return self

        def decide(self, path, permission):
            return SimpleNamespace(status="allowed", reason_code="allowed")

    monkeypatch.setattr(task_runtime_module, "WorkspacePolicyService", lambda: FakeWorkspacePolicy())
    monkeypatch.setattr(task_run_guard_module, "WorkspacePolicyService", lambda: FakeWorkspacePolicy())
    monkeypatch.setattr(task_run_guard_module, "WorkspaceRoleContractService", lambda: FakeWorkspaceRoleContracts())
    monkeypatch.setattr(task_run_guard_module, "WorkspacePermissionMatrixService", lambda: FakePermissionMatrix())
    workspace = tmp_path / "App"
    now = datetime.now(timezone.utc).isoformat()
    draft_store = TaskDraftStore(tmp_path / "drafts")
    preview_store = TaskPreviewStore(tmp_path / "previews")
    approval_store = ApprovalStore(tmp_path / "approvals")
    run_store = TaskRunStore(tmp_path / "runs")
    preview_service = TaskPreviewService(store=preview_store, draft_store=draft_store)
    approvals = ApprovalService(
        store=approval_store,
        preview_service=preview_service,
        draft_store=draft_store,
    )
    draft = TaskContractDraft(
        draft_id="draft_runtime_custom_store",
        session_id="chat_test",
        status="approval_required",
        intent_map={
            "risk": "medium",
            "target_path": str(workspace),
            "target_paths": [str(workspace / "runtime.txt")],
            "context_ref": "test_context",
            "validation_plan": {"checks": ["file_exists"]},
            "rollback_plan": {"strategy": "delete_test_fixture"},
            "project_generation_plan": {
                "target_workspace": str(workspace),
                "files_to_modify": [{"path": "runtime.txt", "content": "from custom draft store", "overwrite": True}],
                "validation_steps": ["file_exists"],
                "expected_outputs": ["runtime.txt"],
            },
        },
        policy_decision={
            "decision_id": "policy_runtime_custom_store",
            "status": "ask",
            "approval_required_for": ["write_files"],
        },
        contract_type="project_generation",
        operation_type="project_generation",
        runtime_profile="project_generation",
        capabilities_required=["write_workspace"],
        source_scope="test_harness",
        requires_workspace=True,
        workspace=TaskDraftWorkspace(path=str(workspace), status="confirmed"),
        requested_actions=["write_files"],
        allowed_actions=[],
        denied_actions=[],
        approval_required_for=["write_files"],
        executable_plan_ref="draft_runtime_custom_store:project_generation_plan",
        expected_outcomes=["project_generation", "validation_result"],
        safe_to_execute=False,
        safe_to_preview=True,
        created_at=now,
        updated_at=now,
    )
    draft_store.save(draft)
    preview = preview_service.create_preview_from_draft(draft.draft_id)
    assert preview is not None
    approval = approvals.create_approval_for_preview(preview.preview_id, actions=["write_files"], reason="test")
    approvals.approve(approval.approval_id, reason="test")
    runtime = TaskRuntimeService(
        store=run_store,
        drafts=TaskContractDraftService(store=draft_store),
        previews=preview_service,
        approvals=approvals,
    )

    run = runtime.create_from_preview(
        preview.preview_id,
        {"approval_id": approval.approval_id, "start_immediately": True},
    )
    process = runtime.process_queue()

    latest = runtime.get_run(run.run_id)
    assert process["status"] in {"completed", "queue_empty"}
    assert latest is not None
    assert latest.status == "completed", latest.blocked_reasons
    assert (workspace / "runtime.txt").read_text(encoding="utf-8") == "from custom draft store"
