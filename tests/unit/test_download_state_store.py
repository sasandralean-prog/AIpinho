from apps.launcher.ui.state.download_state_store import DownloadStateStore


def test_download_state_store_roundtrip(tmp_path) -> None:
    store = DownloadStateStore(tmp_path / "state.json")
    store.set("artifact_id", "value")
    assert store.get("artifact_id") == "value"
    assert store.clear() == {}
