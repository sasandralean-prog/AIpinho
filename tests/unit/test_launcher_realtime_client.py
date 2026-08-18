from __future__ import annotations

import json

def transport(status=200, data=None):
    def _transport(method, url, headers, body, timeout):
        payload = data if data is not None else {"method": method, "url": url, "headers": headers, "body": body.decode("utf-8") if body else None}
        return status, payload
    return _transport

from apps.launcher.ui.api.realtime_client import RealtimeClient


def test_realtime_client_parse_sse_and_since() -> None:
    client = RealtimeClient("http://127.0.0.1:9089", transport=transport(data={"status": "ok"}))
    parsed = client.parse_sse('id: 1\nevent: change\ndata: {"cursor":"1"}\n\n')
    assert parsed[0]["cursor"] == "1"
    assert client.since("0").ok
