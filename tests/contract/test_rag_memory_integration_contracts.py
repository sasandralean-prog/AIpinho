from aipinho.schemas.rag.integration.contracts import (
    ContextAdmissionDecision,
    ContextAdmissionRequest,
    ContextCitationMap,
    ContextInjectionItem,
    ContextInjectionPlan,
    ContextProvenance,
    RAGMemoryPolicyDecision,
    RAGMemoryPolicyRequest,
)
from tests.unit.rag_memory_test_helpers import admitted_retrieval, explicit_policy


def test_policy_contracts_validate():
    request = RAGMemoryPolicyRequest(usage_mode="explicit_user_request", requested_sources=["project_reports"], allow_retrieval=True)
    decision = RAGMemoryPolicyDecision(usage_mode=request.usage_mode, allowed=True, status="allowed")
    assert request.usage_mode == decision.usage_mode


def test_admission_and_plan_contracts_validate():
    admission = admitted_retrieval()
    restored = ContextAdmissionDecision.model_validate(admission.model_dump())
    plan = ContextInjectionPlan(context_items=restored.admitted_items, citation_map=restored.citation_map, safe_for_prompt_assembly=True, status="ready")
    assert plan.context_items
    assert plan.citation_map.valid is True


def test_context_item_provenance_and_citation_map_contracts_validate():
    item = admitted_retrieval().admitted_items[0]
    restored_item = ContextInjectionItem.model_validate(item.model_dump())
    restored_provenance = ContextProvenance.model_validate(item.provenance.model_dump())
    citation_map = ContextCitationMap(item_to_citations={item.context_item_id: item.citation_ids}, citations={item.citation_ids[0]: {"source_ref": {"ref": "reports/status.md"}}}, valid=True)
    assert restored_item.provenance.citation_id == restored_provenance.citation_id
    assert citation_map.valid is True


def test_admission_request_contract_accepts_policy_and_context():
    result = ContextAdmissionRequest(policy_decision=explicit_policy())
    assert result.policy_decision.requires_context_admission is True

