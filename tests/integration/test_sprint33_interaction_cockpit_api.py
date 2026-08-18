from __future__ import annotations

from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from aipinho.services.security.local_token_service import LocalTokenService


def test_chat_session_message_copy_feedback_and_sync_snapshot() -> None:
    client = TestClient(create_app())

    session_response = client.post("/api/v1/chat/sessions", json={"title": "Sprint 33 API"})
    assert session_response.status_code == 200
    session_id = session_response.json()["session"]["session_id"]

    content = "Mensagem humana completa " * 120
    message_response = client.post(f"/api/v1/chat/sessions/{session_id}/messages", json={"role": "user", "content": content})
    assert message_response.status_code == 200
    message_id = message_response.json()["message"]["message_id"]
    assert message_response.json()["message"]["chunk_total"] > 1

    timeline_response = client.get(f"/api/v1/chat/sessions/{session_id}/timeline")
    assert timeline_response.status_code == 200
    assert timeline_response.json()["timeline"]["messages"]

    copy_response = client.get(f"/api/v1/chat/messages/{message_id}/copy")
    assert copy_response.status_code == 200
    assert copy_response.json()["copy"]["text"] == content

    feedback_response = client.post(f"/api/v1/chat/messages/{message_id}/feedback", json={"target_type": "chat_message", "target_id": message_id, "rating": "like", "reason": "util"})
    assert feedback_response.status_code == 200
    feedback = feedback_response.json()["feedback"]
    assert feedback["auto_memory_mutation"] is False
    assert feedback["evaluation_signal_created"] is True

    snapshot_response = client.get("/api/v1/sync/snapshot")
    assert snapshot_response.status_code == 200
    assert snapshot_response.json()["snapshot"]["cursor"] is not None


def test_artifact_upload_metadata_download_zip_and_token_gate() -> None:
    client = TestClient(create_app())
    upload_response = client.post("/api/v1/artifacts/upload", json={"filename": "sprint33.txt", "content": "artifact seguro", "content_type": "text/plain"})
    assert upload_response.status_code == 200
    artifact = upload_response.json()["upload"]["artifact"]
    artifact_id = artifact["artifact_id"]
    assert artifact["direct_workspace_file"] is False

    metadata_response = client.get(f"/api/v1/artifacts/{artifact_id}/metadata")
    assert metadata_response.status_code == 200
    assert metadata_response.json()["status"] == "ok"

    unauthenticated = client.get(f"/api/v1/artifacts/{artifact_id}/download")
    assert unauthenticated.status_code == 401

    token = LocalTokenService().create_token(status="created").token
    authenticated = client.get(f"/api/v1/artifacts/{artifact_id}/download", headers={"Authorization": f"Bearer {token}"})
    assert authenticated.status_code == 200
    assert authenticated.content == b"artifact seguro"

    zip_response = client.post("/api/v1/artifacts/zip", json={"artifact_ids": [artifact_id], "filename": "bundle.zip"})
    assert zip_response.status_code == 200
    zip_id = zip_response.json()["zip"]["artifact"]["artifact_id"]
    zip_download = client.get(f"/api/v1/artifacts/zip/{zip_id}/download", headers={"Authorization": f"Bearer {token}"})
    assert zip_download.status_code == 200
    assert zip_download.content.startswith(b"PK")


def test_event_api_blocks_unknown_and_exposes_public_payload() -> None:
    client = TestClient(create_app())
    blocked = client.post("/api/v1/events/publish", json={"event_type": "ghost_event", "source_service": "chat", "human_summary": "Nunca renderizar normal."})
    assert blocked.status_code == 409

    created = client.post("/api/v1/events/publish", json={"event_type": "message_received", "source_service": "chat", "human_summary": "Mensagem registrada.", "payload": {"session_id": "session_api"}})
    assert created.status_code == 200
    event = created.json()["event"]
    assert event["raw_available"] is False
    detail = client.get(f"/api/v1/events/{event['event_id']}")
    assert detail.status_code == 200
    assert detail.json()["event"]["human_summary"] == "Mensagem registrada."
