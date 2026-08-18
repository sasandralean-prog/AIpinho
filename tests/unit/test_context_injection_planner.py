from aipinho.schemas.rag.integration.contracts import ContextAdmissionDecision
from aipinho.services.rag.integration.context_injection_planner import ContextInjectionPlanner
from aipinho.services.rag.integration.context_usage_audit_service import ContextUsageAuditService
from tests.unit.rag_memory_test_helpers import admitted_retrieval


def planner(tmp_path):
    return ContextInjectionPlanner(audit=ContextUsageAuditService(root=tmp_path / "plans"))


def test_ready_plan_includes_citation_map_and_budget(tmp_path):
    plan = planner(tmp_path).plan(admitted_retrieval())
    assert plan.status == "ready"
    assert plan.safe_for_prompt_assembly is True
    assert plan.citation_map.valid is True
    assert plan.budget_summary.admitted_items == 1


def test_blocked_admission_creates_blocked_plan(tmp_path):
    blocked = ContextAdmissionDecision(status="blocked", blocked_reasons=["no_admissible_context"])
    plan = planner(tmp_path).plan(blocked)
    assert plan.status == "blocked"
    assert plan.safe_for_prompt_assembly is False


def test_missing_citation_map_blocks_plan(tmp_path):
    admission = admitted_retrieval()
    admission.citation_map.item_to_citations = {}
    admission.citation_map.valid = False
    plan = planner(tmp_path).plan(admission)
    assert plan.status == "blocked"
    assert plan.blocked_reasons

