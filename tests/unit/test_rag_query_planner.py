from aipinho.schemas.rag.vector.contracts import RAGQueryRequest
from aipinho.services.rag.vector.rag_query_planner import RAGQueryPlanner


def test_rag_query_planner_blocks_cross_role_namespace_and_uses_global_by_default():
    planner = RAGQueryPlanner()

    global_plan = planner.plan(RAGQueryRequest(query="AIpinho"))
    assert global_plan["status"] == "ok"
    assert "global_ecosystem" in global_plan["namespace_ids"]

    blocked = planner.plan(RAGQueryRequest(query="review code", role_id="planner", namespace_id="coder_rag"))
    assert blocked["status"] == "blocked"
    assert "cross_role_namespace_blocked" in blocked["blocked_reasons"]
