from apps.launcher.ui.state.ui_state_store import JsonStateStore


def test_ui_state_store_roundtrip(tmp_path) -> None:
    store = JsonStateStore(tmp_path / "state.json")
    store.set("selected_profile", "wifi_lan")
    assert store.get("selected_profile") == "wifi_lan"
