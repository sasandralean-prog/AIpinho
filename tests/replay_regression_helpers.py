from __future__ import annotations

from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)


def capture_snapshot(prompt: str = "hello") -> dict[str, object]:
    response = client.post(
        "/api/v1/replay/capture",
        json={
            "reason": "test capture",
            "prompt": prompt,
            "snapshot_payload": {
                "decision_bundle": {"policy_decision": {"write_allowed": False}},
                "events": [{"event_type": "message_received"}],
            },
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["snapshot"]


def create_replay_case() -> dict[str, object]:
    snapshot = capture_snapshot()
    response = client.post(
        "/api/v1/replay/cases",
        json={"snapshot_id": snapshot["metadata"]["snapshot_id"], "title": "Regression fixture"},
    )
    assert response.status_code == 200, response.text
    return response.json()["case"]


def create_regression_candidate() -> dict[str, object]:
    snapshot = capture_snapshot()
    response = client.post(
        "/api/v1/regression/candidates",
        json={
            "source_type": "maintenance",
            "category": "policy",
            "severity": "high",
            "evidence": [{"source": "test"}],
            "expected_behavior": {"write_allowed": False},
            "snapshot_id": snapshot["metadata"]["snapshot_id"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["candidate"]
