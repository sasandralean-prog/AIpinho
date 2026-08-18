from apps.launcher.ui.state.event_cursor_store import EventCursorStore


def test_event_cursor_store_roundtrip(tmp_path) -> None:
    store = EventCursorStore(tmp_path / "state.json")
    store.set("cursor", "value")
    assert store.get("cursor") == "value"
    assert store.clear() == {}
