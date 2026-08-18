from aipinho.schemas.models.manual_inference_result import ManualInferenceResult
from aipinho.services.models.real_inference_run_store import RealInferenceRunStore


def test_real_inference_run_store_saves_runs_and_events(tmp_path):
    store = RealInferenceRunStore(config={"store": {"runs_dir": str(tmp_path / "runs"), "events_dir": str(tmp_path / "events")}})
    result = ManualInferenceResult(status="blocked", output_preview="OK")
    run = store.save_run(result)
    loaded = store.get_run(run.run_id)
    assert loaded is not None
    assert loaded["run_id"] == run.run_id
    assert loaded["output_preview"] == "OK"
    store.append_event(run.run_id, {"event": "smoke_test_blocked", "run_id": run.run_id})
    assert store.list_events(run.run_id)[0]["event"] == "smoke_test_blocked"


def test_real_inference_run_store_missing_run_returns_none(tmp_path):
    store = RealInferenceRunStore(config={"store": {"runs_dir": str(tmp_path / "runs"), "events_dir": str(tmp_path / "events")}})
    assert store.get_run("missing") is None
    assert store.list_events("missing") == []
