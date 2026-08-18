from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


client = TestClient(create_app())


def _payload(
    *,
    source_agent: str = "lucio",
    content: str = "artifact body",
    filename: str | None = None,
    owner_task_id: str | None = None,
    bridge_task_id: str | None = None,
    session_id: str | None = None,
    visible_to_agent_ids: list[str] | None = None,
) -> dict[str, object]:
    token = uuid4().hex
    return {
        "source_agent": source_agent,
        "filename": filename or f"artifact_{token}.md",
        "content": content,
        "content_type": "text/markdown",
        "owner_task_id": owner_task_id,
        "bridge_task_id": bridge_task_id,
        "session_id": session_id,
        "provenance": {"test_ref": token},
        "visible_to_agent_ids": visible_to_agent_ids or [],
    }


def test_artifact_registry_creates_text_artifact() -> None:
    response = client.post("/api/v1/artifacts", json=_payload(source_agent="lucio"))

    assert response.status_code == 200
    assert response.json()["source"] == "universal_artifact_registry_compat"
    assert response.json()["compatibility_warning"] == "legacy_universal_artifact_creation_without_complete_runtime_binding"
    artifact = response.json()["artifact"]
    assert artifact["artifact_id"]
    assert artifact["source_agent"] == "lucio"
    assert artifact["status"] == "ready"
    assert artifact["size_bytes"] > 0
    assert artifact["download_endpoint"] == f"/api/v1/artifacts/{artifact['artifact_id']}/download"
    assert artifact["requires_token"] is True


def test_artifact_registry_uses_runtime_when_public_contract_has_full_binding() -> None:
    task_id = f"task_{uuid4().hex}"
    task_run_id = f"run_{uuid4().hex}"
    response = client.post(
        "/api/v1/artifacts",
        json={
            **_payload(source_agent="aipinho_runtime", filename="phase1.md"),
            "logical_path": "reports/firetest5/phase1.md",
            "producer_step": "phase1_discovery",
            "event_id": f"event_{uuid4().hex}",
            "task_id": task_id,
            "task_run_id": task_run_id,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "artifact_runtime"
    assert payload["compatibility_warning"] is None
    artifact = payload["artifact"]
    assert artifact["logical_path"] == "reports/firetest5/phase1.md"
    assert artifact["task_id"] == task_id
    assert artifact["task_run_id"] == task_run_id
    assert artifact["producer_step"] == "phase1_discovery"
    assert artifact["provenance"]["artifact_runtime"] == "canonical"


def test_artifact_registry_rejects_missing_file_ready() -> None:
    response = client.post(
        "/api/v1/artifacts",
        json={
            "source_agent": "codex_agent",
            "filename": "missing.md",
            "local_path": "C:/path/that/does/not/exist/missing.md",
            "status": "ready",
        },
    )

    assert response.status_code == 404


def test_artifact_registry_download_requires_auth_when_configured() -> None:
    artifact = client.post("/api/v1/artifacts", json=_payload(source_agent="gemini_executor")).json()["artifact"]

    response = client.get(artifact["download_endpoint"])

    assert response.status_code == 401


def test_artifact_registry_lists_by_agent_task_and_bridge_task() -> None:
    owner_task_id = f"task_{uuid4().hex}"
    bridge_task_id = f"bridge_{uuid4().hex}"
    session_id = f"session_{uuid4().hex}"
    created = client.post(
        "/api/v1/artifacts",
        json=_payload(
            source_agent="codex_agent",
            owner_task_id=owner_task_id,
            bridge_task_id=bridge_task_id,
            session_id=session_id,
        ),
    ).json()["artifact"]

    by_agent = client.get(f"/api/v1/artifacts/by-agent/codex_agent?session_id={session_id}").json()["artifacts"]
    by_task = client.get(f"/api/v1/artifacts/by-task/{owner_task_id}").json()["artifacts"]
    by_bridge = client.get(f"/api/v1/artifacts/by-bridge-task/{bridge_task_id}").json()["artifacts"]

    assert created["artifact_id"] in {item["artifact_id"] for item in by_agent}
    assert created["artifact_id"] in {item["artifact_id"] for item in by_task}
    assert created["artifact_id"] in {item["artifact_id"] for item in by_bridge}


def test_delegated_aipinho_artifact_visible_to_source_agent() -> None:
    bridge_task_id = f"bridge_{uuid4().hex}"
    session_id = f"lucio_session_{uuid4().hex}"
    created = client.post(
        "/api/v1/artifacts",
        json=_payload(
            source_agent="aipinho",
            bridge_task_id=bridge_task_id,
            session_id=session_id,
            visible_to_agent_ids=["lucio"],
        ),
    ).json()["artifact"]

    by_lucio = client.get(f"/api/v1/artifacts/by-agent/lucio?session_id={session_id}").json()["artifacts"]
    by_bridge = client.get(f"/api/v1/artifacts/by-bridge-task/{bridge_task_id}").json()["artifacts"]

    assert created["artifact_id"] in {item["artifact_id"] for item in by_lucio}
    assert created["artifact_id"] in {item["artifact_id"] for item in by_bridge}


def test_lucio_gemini_and_codex_text_artifacts_registered() -> None:
    for agent_id in ("lucio", "gemini_executor", "codex_agent"):
        created = client.post("/api/v1/artifacts", json=_payload(source_agent=agent_id)).json()["artifact"]
        listed = client.get(f"/api/v1/artifacts/by-agent/{agent_id}").json()["artifacts"]
        assert created["artifact_id"] in {item["artifact_id"] for item in listed}
