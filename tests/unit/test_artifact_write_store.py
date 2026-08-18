from aipinho.schemas.artifacts.artifact_write_event import ArtifactWriteEvent
from aipinho.schemas.artifacts.artifact_write_result import ArtifactWriteResult
from aipinho.schemas.artifacts.artifact_write_run import ArtifactWriteRun
from aipinho.services.artifacts.artifact_write_store import ArtifactWriteStore


def test_write_store_run_events_result_trace(tmp_path):
    store = ArtifactWriteStore(root=tmp_path / "writes")
    run = ArtifactWriteRun(write_run_id="artifact_write_run_abcdef", preview_id="p", approval_id="a", workspace=str(tmp_path), target_path="reports/a.md", created_at="now", updated_at="now")
    store.create_run(run)
    assert store.get_run(run.write_run_id).write_run_id == run.write_run_id
    event = ArtifactWriteEvent(event_id="e", write_run_id=run.write_run_id, event_type="created", created_at="now")
    store.append_event(event)
    assert store.get_events(run.write_run_id)[0].event_type == "created"
    result = ArtifactWriteResult(write_run_id=run.write_run_id, preview_id="p", approval_id="a", status="blocked", target_path="reports/a.md", created_at="now")
    store.save_result(result)
    assert store.get_result(run.write_run_id).status == "blocked"
    store.save_trace(run.write_run_id, ["a"])
    assert store.get_trace(run.write_run_id) == ["a"]
