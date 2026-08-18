from pathlib import Path

from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService


def snapshot_files(root: Path) -> dict[str, str]:
    return {str(path.relative_to(root)): path.read_text(encoding="utf-8") for path in root.rglob("*") if path.is_file()}


def test_readonly_task_runtime_supervised_loop_does_not_write_workspace(readonly_workspace, task_runtime_store):
    before = snapshot_files(readonly_workspace)
    service = TaskRuntimeService(store=task_runtime_store)
    run = service.create_run(
        TaskRunRequest(
            source_type="direct",
            session_id="session_e2e",
            workspace=str(readonly_workspace),
            contract_type="readonly_analysis",
            intent_map={"intent_type": "readonly_analysis"},
            policy_decision={"status": "allowed", "approval_required_for": []},
            requested_actions=[],
        )
    )

    finished, result = service.start(run.run_id)
    after = snapshot_files(readonly_workspace)

    assert finished.status in {"completed", "partial"}
    assert result.status in {"completed", "partial"}
    assert result.safe_to_display is True
    assert after == before
    assert service.get_events(run.run_id)
    assert service.get_trace(run.run_id)
