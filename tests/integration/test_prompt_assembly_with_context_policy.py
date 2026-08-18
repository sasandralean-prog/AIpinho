from fastapi.testclient import TestClient

from aipinho.app_factory import create_app
from tests.unit.rag_memory_test_helpers import ready_plan

client = TestClient(create_app())


def assemble(payload):
    base = {"purpose": "chat", "role_id": "speaker", "user_message": "Summarize context."}
    base.update(payload)
    return client.post("/api/v1/prompts/assemble", json=base).json()["assembly"]


def test_valid_plan_is_accepted_with_citations(tmp_path):
    plan = ready_plan(tmp_path)
    assembly = assemble({"context_injection_plan": plan.model_dump()})
    assert any(item["title"] == "Governed Context" for item in assembly["context_items"])
    assert str(next(iter(plan.citation_map.citations))) in str(assembly["messages"])


def test_raw_retrieval_context_payload_is_not_injected():
    assembly = assemble({"retrieval_context_bundle": {"safe_for_prompt_assembly": True, "citations": [{"citation_id": "citation_x"}], "context_text": "raw"}})
    assert not any(item["title"] == "Governed retrieval context" for item in assembly["context_items"])
    assert "direct_retrieval_context_requires_plan" in assembly["warnings"]


def test_unsafe_plan_is_rejected():
    assembly = assemble({"context_injection_plan": {"status": "blocked", "safe_for_prompt_assembly": False}})
    assert not any(item["title"] == "Governed Context" for item in assembly["context_items"])
    assert "context_injection_plan_unsafe" in assembly["warnings"]

