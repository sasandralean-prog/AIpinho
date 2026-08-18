from apps.launcher.ui.state.raw_viewer_state_store import RawViewerStateStore
def test_raw_viewer_store_closed_default():
    s=RawViewerStateStore(); assert s.get("open",False) is False
