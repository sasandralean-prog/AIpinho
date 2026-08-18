from apps.launcher.ui.state.reconnect_state_store import ReconnectStateStore
def test_reconnect_store_snapshots():
    s=ReconnectStateStore(); s.set("cursor","1"); assert s.snapshot()["cursor"]=="1"
