from __future__ import annotations

import json

def transport(status=200, data=None):
    def _transport(method, url, headers, body, timeout):
        payload = data if data is not None else {"method": method, "url": url, "headers": headers, "body": body.decode("utf-8") if body else None}
        return status, payload
    return _transport

from apps.launcher.ui.api.chat_client import ChatClient


def test_chat_client_sessions_messages_raw_feedback() -> None:
    client = ChatClient("http://127.0.0.1:9088", transport=transport(data={"status": "ok"}))
    assert client.list_sessions().ok
    assert client.create_session("Teste").ok
    assert client.rename_session("s1", "Novo nome").ok
    assert client.delete_session("s1").ok
    assert client.send_message("s1", "ola").ok
    assert client.record_message("s1", "rascunho").ok
    assert client.timeline("s1").ok
    assert client.feedback("m1", "like").ok


def test_chat_client_send_uses_persistent_send_endpoint() -> None:
    client = ChatClient("http://127.0.0.1:9088", transport=transport())
    result = client.send_message("s1", "ola")

    assert result.ok
    assert result.data["url"].endswith("/api/v1/chat/sessions/s1/send")
    body = json.loads(result.data["body"])
    assert body == {"role": "user", "content": "ola", "metadata": {}}


def test_chat_client_record_message_is_explicit_record_only() -> None:
    client = ChatClient("http://127.0.0.1:9088", transport=transport())
    result = client.record_message("s1", "rascunho")

    assert result.ok
    assert result.data["url"].endswith("/api/v1/chat/sessions/s1/messages")
    body = json.loads(result.data["body"])
    assert body == {"role": "user", "content": "rascunho", "metadata": {}}


def test_chat_client_rename_and_delete_session_use_canonical_session_endpoint() -> None:
    client = ChatClient("http://127.0.0.1:9088", transport=transport())

    renamed = client.rename_session("s1", "Minha conversa")
    deleted = client.delete_session("s1")

    assert renamed.ok
    assert renamed.data["method"] == "PATCH"
    assert renamed.data["url"].endswith("/api/v1/chat/sessions/s1")
    assert json.loads(renamed.data["body"]) == {"title": "Minha conversa"}
    assert deleted.ok
    assert deleted.data["method"] == "DELETE"
    assert deleted.data["url"].endswith("/api/v1/chat/sessions/s1")
