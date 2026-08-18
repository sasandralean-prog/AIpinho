from __future__ import annotations

from fastapi import APIRouter

from aipinho.services.rag.integration.context_admission_service import ContextAdmissionService
from aipinho.services.rag.integration.context_injection_planner import ContextInjectionPlanner
from aipinho.services.rag.integration.context_usage_validator import ContextUsageValidator
from aipinho.services.rag.integration.rag_memory_policy_service import RAGMemoryPolicyService
from aipinho.services.rag.integration.rag_memory_status_service import RAGMemoryStatusService

router = APIRouter(prefix="/api/v1/context-policy", tags=["context-policy"])


@router.get("/status")
def get_context_policy_status() -> dict[str, object]:
    return {
        "status": "ok",
        "policy": RAGMemoryPolicyService().status(),
        "admission": ContextAdmissionService().status(),
        "planner": ContextInjectionPlanner().status(),
        "validator": ContextUsageValidator().status(),
        "integration": RAGMemoryStatusService().status(),
    }
