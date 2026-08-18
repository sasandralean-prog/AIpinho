from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from tests.support.runtime_fixtures import runtime_run


def test_runtime_truth_uses_lightweight_run_projection_for_terminal_block(task_runtime_store, monkeypatch) -> None:
    run = runtime_run(status="blocked")
    task_runtime_store.create_run(run)
    task_runtime_store.save_result(run.run_id, TaskRunResult(run_id=run.run_id, status="blocked", summary="blocked"))
    runtime = TaskRuntimeService(store=task_runtime_store)
    called = {"lightweight": False}
    original = task_runtime_store.get_run_lightweight

    def spy(run_id):
        called["lightweight"] = True
        return original(run_id)

    monkeypatch.setattr(task_runtime_store, "get_run_lightweight", spy)

    truth = runtime.get_runtime_truth(run.run_id)

    assert called["lightweight"] is True
    assert truth is not None
    assert truth.safe_to_report_success is False
