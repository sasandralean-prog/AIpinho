from apps.launcher.ui.state.token_state_store import TokenStateStore


def test_token_state_store_roundtrip(tmp_path) -> None:
    store = TokenStateStore(tmp_path / "state.json")
    store.set("token", "value")
    assert store.get("token") == "value"
    assert store.clear() == {}
