from __future__ import annotations

import json

def transport(status=200, data=None):
    def _transport(method, url, headers, body, timeout):
        payload = data if data is not None else {"method": method, "url": url, "headers": headers, "body": body.decode("utf-8") if body else None}
        return status, payload
    return _transport

from apps.launcher.ui.api.event_contract_client import EventContractClient


def test_event_contract_client_registry_and_ownership() -> None:
    client = EventContractClient("http://127.0.0.1:9088", transport=transport(data={"status": "ok", "contracts": {"message_received": {}}}))
    assert client.status().ok
    assert client.contracts().data["contracts"]
    assert client.ownership().ok
