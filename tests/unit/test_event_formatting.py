from apps.launcher.ui.utils.event_formatting import event_title, is_unknown_event


def test_event_formatting_unknown() -> None:
    assert "message_received" in event_title({"event_type": "message_received", "severity": "info", "source_service": "chat"})
    assert is_unknown_event({"event_type": "ghost"}, {"message_received"}) is True
