from __future__ import annotations

from fastapi.testclient import TestClient

from aipinho.main import app

client = TestClient(app)


def test_capabilities_endpoint_lists_all_core_capabilities():
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    data = response.json()
    ids = {item["capability_id"] for item in data["capabilities"]}
    assert {
        "text_chat",
        "code_assist",
        "planning",
        "intent_classification",
        "policy_reasoning",
        "embeddings",
        "reranker",
        "ocr",
        "vision",
        "workspace_search",
        "file_summarization",
        "patch_planning",
        "shell_planning",
        "artifact_summary",
    } <= ids


def test_capability_health_reports_missing_or_disabled_not_fake_ready():
    response = client.get("/api/v1/capabilities/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ok", "degraded"}
    for item in data["capabilities"]:
        assert item["health_status"] in {"ok", "missing", "disabled", "unverified", "failed"}
        if item["capability_id"] in {"ocr", "vision"}:
            assert item["health_status"] in {"disabled", "missing", "unverified", "ok"}


def test_model_registry_and_capability_router_load():
    registry = client.get("/api/v1/models/registry")
    router = client.get("/api/v1/models/router")

    assert registry.status_code == 200
    assert router.status_code == 200
    assert registry.json()["status"] == "ok"
    assert "route_matrix" in router.json()


def test_route_preview_returns_selected_capability_and_records_decision():
    response = client.get("/api/v1/models/route-preview", params={"operation_type": "continue_context_analysis"})
    assert response.status_code == 200
    decision = response.json()["route_decision"]
    assert decision["operation_type"] == "continue_context_analysis"
    assert "code_assist" in decision["required_capabilities"]
    assert decision["selected_capabilities"][0]["provider"]


def test_router_test_embeddings_ok_or_missing_structured():
    response = client.post("/api/v1/models/router/test", json={"capability": "embeddings", "input": "AIpinho teste"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ok", "missing", "failed", "disabled", "unverified"}
    assert data["capability"] == "embeddings"
    assert "provider" in data
    assert "model" in data


def test_workspace_search_falls_back_to_keyword_if_no_embeddings(tmp_path):
    source = tmp_path / "sample.txt"
    source.write_text("AIpinho workspace search keyword sample", encoding="utf-8")

    response = client.post(
        "/api/v1/capabilities/workspace-search",
        json={"query": "keyword", "workspace_path": str(tmp_path), "limit": 5},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"ok", "blocked"}
    if data["status"] == "ok":
        assert data["capabilities_used"]["fallback"] == "keyword_search"
        assert data["capabilities_used"]["embeddings_used"] is False
        assert data["capabilities_used"]["reranker_used"] is False


def test_continue_route_decision_event_emitted_for_continue():
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "aipinho-local",
            "stream": False,
            "messages": [{"role": "user", "content": "@App.tsx\nExplique este arquivo."}],
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert "model_route_decision" in data["aipinho"]
    assert data["aipinho"]["model_route_decision"]["source_channel"] == "vscode_continue"
