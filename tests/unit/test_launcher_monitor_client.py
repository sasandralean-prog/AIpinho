from __future__ import annotations

import json

def transport(status=200, data=None):
    def _transport(method, url, headers, body, timeout):
        payload = data if data is not None else {"method": method, "url": url, "headers": headers, "body": body.decode("utf-8") if body else None}
        return status, payload
    return _transport

from apps.launcher.ui.api.monitor_client import MonitorClient


def test_monitor_client_restart_policy() -> None:
    client = MonitorClient("http://127.0.0.1:9099", transport=transport(data={"status": "ok"}))
    assert client.can_restart_port(9088) is True
    assert client.can_restart_port(9099) is False
    blocked = client.restart_service("monitor_supervisor", port=9099)
    assert blocked.ok is False
    assert blocked.status_code == 409
