from __future__ import annotations

import json

def transport(status=200, data=None):
    def _transport(method, url, headers, body, timeout):
        payload = data if data is not None else {"method": method, "url": url, "headers": headers, "body": body.decode("utf-8") if body else None}
        return status, payload
    return _transport

from apps.launcher.ui.api.debugger_client import DebuggerClient


def test_debugger_client_read_only_endpoints() -> None:
    client = DebuggerClient("http://127.0.0.1:9088", transport=transport(data={"status": "ok"}))
    assert client.status().ok
    assert client.trace_timeline("trace_1").ok
    assert client.model_run("run_1").ok
    assert client.rag_run("rag_1").ok
