from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService
from tests.support.runtime_fixtures import runtime_run


def test_summary_projects_finished_at_for_terminal_run(task_runtime_store) -> None:
    run = runtime_run(status="running")
    task_runtime_store.create_run(run)
    task_runtime_store.save_result(run.run_id, TaskRunResult(run_id=run.run_id, status="blocked", summary="blocked"))

    summary = UniversalTaskSessionService(store=task_runtime_store).summary(run.run_id)

    assert summary is not None
    assert summary["status"] == "BLOCKED"
    assert summary["finished_at"]
