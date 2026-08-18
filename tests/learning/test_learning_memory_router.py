from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from aipinho.api.routers import learning_router, memory_router

ROOT = Path(__file__).resolve().parents[2]


def _fixture(name: str) -> dict:
    return json.loads((ROOT / "tests" / "fixtures" / "learning" / name).read_text(encoding="utf-8"))


def _client(tmp_path: Path, monkeypatch) -> TestClient:
    monkeypatch.setenv("AIPINHO_LEARNING_ROOT", str(tmp_path / "learning"))
    app = FastAPI()
    app.include_router(learning_router.router)
    app.include_router(learning_router.mobile_router)
    app.include_router(memory_router.router)
    return TestClient(app)


def test_learning_extract_and_memory_candidate_review_endpoints(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)

    extracted = client.post("/api/v1/learning/extract", json=_fixture("valid_run_learning.json"))

    assert extracted.status_code == 200
    payload = extracted.json()
    assert payload["status"] == "candidates_created"
    candidate_id = payload["candidates"][0]["candidate_id"]
    assert client.get(f"/api/v1/learning/extractions/{payload['extraction_id']}").status_code == 200
    assert client.get(f"/api/v1/learning/extractions/{payload['extraction_id']}/trace").json()["candidate_ids"]
    assert client.get(f"/api/v1/memory/candidates/{candidate_id}").json()["candidate_layer"] == "learning"

    accepted = client.post(f"/api/v1/memory/candidates/{candidate_id}/accept", json={"reviewed_by": "tester"})

    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    query = client.post("/api/v1/memory/query", json={"project_id": "project_fixture", "status": "approved"})
    assert query.status_code == 200
    assert query.json()["total"] >= 1


def test_learning_mobile_view_models_and_profiles(tmp_path: Path, monkeypatch) -> None:
    client = _client(tmp_path, monkeypatch)
    client.post("/api/v1/learning/extract", json=_fixture("valid_run_learning.json"))

    memory_vm = client.get("/api/v1/mobile/view-model/memory")
    learning_vm = client.get("/api/v1/mobile/view-model/learning")
    project = client.get("/api/v1/learning/projects/project_fixture/profile")
    skill_pack = client.get("/api/v1/learning/skill-packs/debug_pack/profile")
    namespaces = client.get("/api/v1/memory/namespaces")

    assert memory_vm.status_code == 200
    assert learning_vm.status_code == 200
    assert memory_vm.json()["state"]["raw_default_visible"] is False
    assert learning_vm.json()["state"]["raw_default_visible"] is False
    assert project.json()["candidate_ids"]
    assert skill_pack.json()["candidate_ids"]
    assert namespaces.json()["namespaces"]
