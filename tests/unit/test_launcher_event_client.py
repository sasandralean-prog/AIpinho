from __future__ import annotations

import json

def transport(status=200, data=None):
    def _transport(method, url, headers, body, timeout):
        payload = data if data is not None else {"method": method, "url": url, "headers": headers, "body": body.decode("utf-8") if body else None}
        return status, payload
    return _transport

from apps.launcher.ui.api.event_client import EventClient


def test_event_client_visibility_and_unknown_handling() -> None:
    client = EventClient("http://127.0.0.1:9088", transport=transport(data={"status": "ok"}))
    assert client.displayable({"event_type": "message_received", "visibility": "public"}, {"message_received"}) is True
    assert client.displayable({"event_type": "unknown", "visibility": "public"}, {"message_received"}) is False
    assert client.displayable({"event_type": "message_received", "visibility": "hidden"}, {"message_received"}) is False
