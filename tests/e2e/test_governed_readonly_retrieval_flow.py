from fastapi.testclient import TestClient

from aipinho.app_factory import create_app


client = TestClient(create_app())


def test_governed_readonly_retrieval_flow_and_no_side_effects():
    status = client.get("/api/v1/rag/status").json()
    assert status["retrieval_mode"] == "governed_read_only"
    assert status["vectorstore_creation_enabled"] is True
    assert status["vector_rag_enabled"] is True
    assert status["embeddings_enabled"] is True
    assert status["auto_ingest_enabled"] is False
    assert status["legacy_vectorstore_enabled"] is False
    assert status["chat_auto_retrieval_enabled"] is False
    assert status["prompt_auto_injection_enabled"] is False

    found = client.post("/api/v1/rag/retrieve/reports", json={"query": "patch apply", "explicit": True}).json()
    assert found["status"] in {"found", "partial"}
    assert found["hits"]
    assert all(hit["citation"] for hit in found["hits"])
    assert found["side_effects"] is False

    blocked = client.post("/api/v1/rag/retrieve", json={"query": "old data", "sources": ["legacy_vectorstore"], "explicit": True}).json()
    assert blocked["status"] == "blocked"

    no_results = client.post("/api/v1/rag/retrieve/reports", json={"query": "zzzz_no_match_zzzz", "explicit": True}).json()
    assert no_results["status"] == "no_results"


def test_chat_explicit_retrieval_and_auto_rag_legacy_blocks():
    explicit = client.post("/api/v1/chat", json={"message": "Busque nos relatorios sobre validation gate."}).json()
    assert explicit["status"] in {"ok", "degraded"}
    assert explicit["context_plan_id"]
    assert "Contexto governado" in explicit["message"]
    auto = client.post("/api/v1/chat", json={"message": "Ative RAG automatico."}).json()
    assert auto["status"] == "blocked"
    legacy = client.post("/api/v1/chat", json={"message": "Use o vectorstore antigo."}).json()
    assert legacy["status"] == "blocked"


def test_prompt_assembly_accepts_only_context_injection_plan():
    retrieval = client.post("/api/v1/rag/retrieve/reports", json={"query": "validation gate", "explicit": True}).json()
    policy = client.post(
        "/api/v1/rag-memory/policy/decide",
        json={"usage_mode": "explicit_user_request", "requested_sources": ["project_reports"], "allow_retrieval": True},
    ).json()
    admission = client.post(
        "/api/v1/rag-memory/context/admit",
        json={"policy_decision": policy, "retrieval_result": retrieval, "retrieval_context_bundle": retrieval["context_bundle"]},
    ).json()
    plan = client.post("/api/v1/rag-memory/context/plan", json=admission).json()
    safe = client.post(
        "/api/v1/prompts/assemble",
        json={
            "purpose": "chat",
            "role_id": "speaker",
            "user_message": "Summarize cited context.",
            "context_injection_plan": plan,
        },
    ).json()
    assert any(item["title"] == "Governed Context" for item in safe["assembly"]["context_items"])

    unsafe_bundle = dict(retrieval["context_bundle"])
    unsafe_bundle["safe_for_prompt_assembly"] = False
    unsafe_bundle["citations"] = []
    unsafe = client.post(
        "/api/v1/prompts/assemble",
        json={
            "purpose": "chat",
            "role_id": "speaker",
            "user_message": "Do not use unsafe context.",
            "retrieval_context_bundle": unsafe_bundle,
        },
    ).json()
    assert not any(item["title"] == "Governed Context" for item in unsafe["assembly"]["context_items"])
    assert "direct_retrieval_context_requires_plan" in unsafe["assembly"]["warnings"]
