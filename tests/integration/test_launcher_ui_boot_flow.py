from apps.launcher.ui.launcher_state import LauncherState


def test_launcher_state_uses_official_ports() -> None:
    state = LauncherState()
    assert state.core_port == 9088
    assert state.realtime_port == 9089
    assert state.artifact_port == 9098
    assert state.monitor_port == 9099
