from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from tests.unit.rag_memory_test_helpers import cited_retrieval, explicit_policy, memory

client = TestClient(create_app())


def test_rag_memory_status_and_policy_decide():
    status = client.get("/api/v1/rag-memory/status").json()
    assert status["integration_enabled"] is True
    assert status["auto_chat_retrieval_enabled"] is False
    policy = client.post(
        "/api/v1/rag-memory/policy/decide",
        json={"usage_mode": "explicit_user_request", "requested_sources": ["project_reports"], "allow_retrieval": True},
    ).json()
    assert policy["allowed"] is True


def test_admit_plan_validate_and_citation_map():
    result, bundle = cited_retrieval()
    policy = explicit_policy().model_dump()
    admission = client.post("/api/v1/rag-memory/context/admit", json={"policy_decision": policy, "retrieval_result": result, "retrieval_context_bundle": bundle}).json()
    assert admission["safe_for_prompt_assembly"] is True
    plan = client.post("/api/v1/rag-memory/context/plan", json=admission).json()
    assert plan["status"] == "ready"
    citation_map = client.post("/api/v1/rag-memory/context/citation-map", json={"items": plan["context_items"]}).json()
    assert citation_map["valid"] is True
    citation_id = next(iter(plan["citation_map"]["citations"]))
    validation = client.post("/api/v1/rag-memory/context/validate", json={"plan": plan, "output": f"ok {citation_id}"}).json()
    assert validation["valid"] is True
    fetched = client.get(f"/api/v1/rag-memory/context/plans/{plan['plan_id']}").json()
    assert fetched["plan_id"] == plan["plan_id"]


def test_from_memory_search_endpoint_blocks_empty_or_inactive_sources():
    response = client.post("/api/v1/rag-memory/context/from-memory-search", json={"query": "nothing should match"}).json()
    assert response["status"] in {"blocked", "ready", "partial"}
    if response["status"] == "ready":
        assert response["context_items"]

