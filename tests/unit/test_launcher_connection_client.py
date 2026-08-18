from __future__ import annotations

import json

def transport(status=200, data=None):
    def _transport(method, url, headers, body, timeout):
        payload = data if data is not None else {"method": method, "url": url, "headers": headers, "body": body.decode("utf-8") if body else None}
        return status, payload
    return _transport

from apps.launcher.ui.api.connection_client import ConnectionClient


def test_connection_client_profiles_and_token() -> None:
    client = ConnectionClient("http://127.0.0.1:9099", transport=transport(data={"status": "ok"}))
    assert client.profiles().ok
    assert client.adb_commands().ok
    assert client.create_token().ok
