from aipinho.services.rag.integration.context_budget_coordinator import ContextBudgetCoordinator
from aipinho.services.rag.integration.context_admission_service import ContextAdmissionService
from aipinho.schemas.rag.integration.contracts import ContextAdmissionRequest
from tests.unit.rag_memory_test_helpers import cited_retrieval, explicit_policy, memory


def test_retrieval_and_memory_share_budget():
    result, bundle = cited_retrieval()
    admission = ContextAdmissionService().admit(
        ContextAdmissionRequest(
            policy_decision=explicit_policy(sources=["project_reports", "curated_memory"]),
            retrieval_result=result,
            retrieval_context_bundle=bundle,
            memory_items=[memory(text="approved memory")],
        )
    )
    assert admission.budget_result.retrieval_items == 1
    assert admission.budget_result.memory_items == 1


def test_budget_truncates_and_omits_by_limits():
    result, bundle = cited_retrieval(text="x" * 3000)
    items = ContextAdmissionService().admit(
        ContextAdmissionRequest(policy_decision=explicit_policy(), retrieval_result=result, retrieval_context_bundle=bundle)
    ).admitted_items
    selected, budget = ContextBudgetCoordinator().apply(items, {"max_context_chars_total": 100, "max_context_chars_per_item": 50})
    assert selected[0].truncated is True
    assert "context_items_truncated_by_budget" in budget.warnings
