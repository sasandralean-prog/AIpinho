from __future__ import annotations

import json

def transport(status=200, data=None):
    def _transport(method, url, headers, body, timeout):
        payload = data if data is not None else {"method": method, "url": url, "headers": headers, "body": body.decode("utf-8") if body else None}
        return status, payload
    return _transport

from apps.launcher.ui.api.base_client import BaseClient


def test_base_client_headers_error_and_redaction() -> None:
    client = BaseClient("http://127.0.0.1:9088", token="secret-token", transport=transport())
    result = client.post("/api/v1/test", {"ok": True})
    assert result.ok is True
    assert result.data["headers"]["Authorization"] == "Bearer secret-token"
    assert "[REDACTED_TOKEN]" in client.redact("secret-token")
