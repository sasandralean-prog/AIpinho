from apps.launcher.ui.utils.event_filtering import filter_events
def test_event_filtering_hides_internal():
    assert filter_events([{"visibility":"internal"},{"visibility":"public","severity":"error"}],severity="error")==[{"visibility":"public","severity":"error"}]
