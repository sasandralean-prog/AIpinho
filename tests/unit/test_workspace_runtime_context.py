from __future__ import annotations

from aipinho.schemas.rag.retrieval_request import RetrievalScope
from aipinho.services.rag.retrieval_service import RetrievalService
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService
from aipinho.services.runtime.workspace_context_service import WorkspaceContextService
from tests.support.runtime_fixtures import runtime_request
from tests.unit.retrieval_test_helpers import request as retrieval_request


class CompletingExecutor:
    def execute_step(self, run, step, context):
        from aipinho.services.runtime.readonly_task_step_runner import TaskStepOutcome

        return TaskStepOutcome(status="completed", summary={"step_type": step.step_type})


def test_task_run_carries_canonical_workspace_retrieval_and_execution_context(task_runtime_service):
    task_runtime_service.loop.executor = CompletingExecutor()
    run = task_runtime_service.create_run(runtime_request(workspace=r"C:\Dev\AIpinho"))

    assert run.workspace_context is not None
    assert run.workspace_context.workspace_id == "aipinho_system"
    assert run.workspace_context.workspace_path == r"C:\Dev\AIpinho"
    assert run.retrieval_context is not None
    assert run.retrieval_context.workspace_id == "aipinho_system"
    assert run.execution_context is not None
    assert run.execution_context.workspace_context is not None
    assert run.execution_context.retrieval_context is not None

    session = UniversalTaskSessionService(store=task_runtime_service.store, approvals=task_runtime_service.approvals).get_session(run.run_id)

    assert session is not None
    assert session.metadata["workspace_context"]["workspace_id"] == "aipinho_system"
    assert session.metadata["retrieval_context"]["workspace_id"] == "aipinho_system"
    assert session.metadata["execution_context"]["task_run_id"] == run.run_id
    assert session.metadata["canonical_runtime_context"]["workspace"]["workspace_id"] == "aipinho_system"


def test_retrieval_uses_canonical_workspace_context_without_manual_workspace():
    service = RetrievalService()
    request = retrieval_request(
        sources=["project_files"],
        workspace=None,
        scope=RetrievalScope(scope_type="workspace"),
        metadata={
            "workspace_context": {
                "workspace_id": "aipinho_system",
                "workspace_path": r"C:\Dev\AIpinho",
                "allowed_roots": [r"C:\Dev\AIpinho"],
                "retrieval_scope": {
                    "workspace": r"C:\Dev\AIpinho",
                    "workspace_id": "aipinho_system",
                    "allowed_roots": [r"C:\Dev\AIpinho"],
                },
            }
        },
    )
    result = service.retrieve(request)

    assert result.status in {"found", "partial", "no_results"}
    assert "workspace_required" not in result.blocked_reasons
    assert "outside_allowed_retrieval_workspace" not in result.blocked_reasons
    assert result.sources_requested == ["project_files"]


def test_workspace_context_preserves_library_roots_distinct_from_project_root(tmp_path):
    project = tmp_path / "project"
    library = tmp_path / "library"
    project.mkdir()
    library.mkdir()

    context = WorkspaceContextService().resolve(
        workspace_path=str(project),
        library_roots=[str(library)],
    )

    assert context.project_root == str(project.resolve())
    assert context.library_roots == [str(library.resolve())]
    assert context.project_root not in context.library_roots
    assert str(library.resolve()) in context.allowed_roots


def test_execution_context_survives_runtime_progress(task_runtime_service):
    task_runtime_service.loop.executor = CompletingExecutor()
    run = task_runtime_service.create_run(runtime_request(workspace=r"C:\Dev\AIpinho"))

    completed, result = task_runtime_service.start(run.run_id)

    assert result.status == "completed"
    assert completed.execution_context is not None
    assert completed.execution_context.phase_history
    assert completed.execution_context.workspace_context is not None
    assert completed.execution_context.retrieval_context is not None
    assert completed.execution_context.phase_history[-1]["status"] == "completed"
