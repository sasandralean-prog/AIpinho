from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.memory.curated_memory import MemorySearchRequest
from aipinho.schemas.rag.integration.contracts import (
    ContextAdmissionDecision,
    ContextAdmissionRequest,
    ContextCitationMap,
    ContextInjectionItem,
    ContextInjectionPlan,
    ContextUsageValidation,
    RAGMemoryPolicyRequest,
)
from aipinho.services.memory.curated_memory_search_service import CuratedMemorySearchService
from aipinho.services.rag.integration.context_admission_service import ContextAdmissionService
from aipinho.services.rag.integration.context_citation_map_service import ContextCitationMapService
from aipinho.services.rag.integration.context_injection_planner import ContextInjectionPlanner
from aipinho.services.rag.integration.context_usage_validator import ContextUsageValidator
from aipinho.services.rag.integration.rag_memory_policy_service import RAGMemoryPolicyService
from aipinho.services.rag.integration.rag_memory_status_service import RAGMemoryStatusService
from aipinho.services.rag.retrieval_service import RetrievalService

router = APIRouter(prefix="/api/v1/rag-memory", tags=["rag-memory"])


class ContextValidationRequest(AIpinhoModel):
    plan_id: str | None = None
    plan: ContextInjectionPlan | None = None
    output: str = ""


class CitationMapRequest(AIpinhoModel):
    items: list[ContextInjectionItem] = Field(default_factory=list)
    citation_map: ContextCitationMap | None = None


class MemoryContextPlanRequest(AIpinhoModel):
    query: str | None = None
    workspace: str | None = None
    scope: str | None = None
    kind: str | None = None
    limit: int = Field(default=4, ge=1, le=20)
    include_trace: bool = False


@router.get("/status")
def get_rag_memory_status() -> dict[str, Any]:
    return RAGMemoryStatusService().status()


@router.post("/policy/decide")
def decide_rag_memory_policy(request: RAGMemoryPolicyRequest) -> dict[str, Any]:
    return RAGMemoryPolicyService().decide(request).model_dump()


@router.post("/context/admit")
def admit_context(request: ContextAdmissionRequest) -> dict[str, Any]:
    return ContextAdmissionService().admit(request).model_dump()


@router.post("/context/plan")
def plan_context(admission: ContextAdmissionDecision) -> dict[str, Any]:
    return ContextInjectionPlanner().plan(admission).model_dump()


@router.post("/context/validate")
def validate_context(request: ContextValidationRequest) -> dict[str, Any]:
    plan = request.plan
    if plan is None and request.plan_id:
        plan = ContextInjectionPlanner().get_plan(request.plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="context_injection_plan_not_found")
    validator = ContextUsageValidator()
    result = validator.validate_output(request.output, plan) if request.output else validator.validate_plan(plan)
    return result.model_dump()


@router.post("/context/citation-map")
def build_or_validate_citation_map(request: CitationMapRequest) -> dict[str, Any]:
    service = ContextCitationMapService()
    result = service.validate(request.citation_map, request.items) if request.citation_map else service.build(request.items)
    return result.model_dump()


@router.post("/context/from-retrieval/{retrieval_id}")
def plan_from_retrieval(retrieval_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    stored = RetrievalService().get_retrieval(retrieval_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="retrieval_not_found")
    payload = payload or {}
    sources = list(stored.get("sources_requested") or stored.get("sources_used") or [])
    policy = RAGMemoryPolicyService().decide(
        RAGMemoryPolicyRequest(
            usage_mode="explicit_user_request",
            intent_type=str(payload.get("intent_type") or "retrieval_context"),
            workspace=payload.get("workspace"),
            requested_sources=sources,
            allow_retrieval=any(source != "curated_memory" for source in sources),
            allow_curated_memory="curated_memory" in sources,
            scope=payload.get("scope") or {},
            user_request=str(payload.get("user_request") or ""),
            include_trace=bool(payload.get("include_trace", False)),
        )
    )
    admission = ContextAdmissionService().admit(
        ContextAdmissionRequest(
            policy_decision=policy,
            retrieval_result=stored,
            retrieval_context_bundle=stored.get("context_bundle"),
            scope={"workspace": payload.get("workspace")} if payload.get("workspace") else {},
            usage_mode="explicit_user_request",
            include_trace=bool(payload.get("include_trace", False)),
        )
    )
    return ContextInjectionPlanner().plan(admission, policy_decision_id=policy.decision_id).model_dump()


@router.post("/context/from-memory-search")
def plan_from_memory_search(request: MemoryContextPlanRequest) -> dict[str, Any]:
    search = CuratedMemorySearchService().search(
        MemorySearchRequest(
            status="active",
            kind=request.kind,
            scope=request.scope,
            workspace=request.workspace,
            text=request.query,
            limit=request.limit,
        )
    )
    policy = RAGMemoryPolicyService().decide(
        RAGMemoryPolicyRequest(
            usage_mode="explicit_user_request",
            intent_type="curated_memory_read",
            workspace=request.workspace,
            requested_sources=["curated_memory"],
            allow_curated_memory=True,
            scope={"workspace": request.workspace} if request.workspace else {},
            user_request=request.query or "",
            include_trace=request.include_trace,
        )
    )
    admission = ContextAdmissionService().admit(
        ContextAdmissionRequest(
            policy_decision=policy,
            memory_items=[item.model_dump() for item in search.results],
            scope={"workspace": request.workspace} if request.workspace else {},
            usage_mode="explicit_user_request",
            include_trace=request.include_trace,
        )
    )
    return ContextInjectionPlanner().plan(admission, policy_decision_id=policy.decision_id).model_dump()


@router.get("/context/plans/{plan_id}")
def get_context_plan(plan_id: str) -> dict[str, Any]:
    try:
        plan = ContextInjectionPlanner().get_plan(plan_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if plan is None:
        raise HTTPException(status_code=404, detail="context_injection_plan_not_found")
    return plan.model_dump()


@router.get("/context/plans/{plan_id}/trace")
def get_context_plan_trace(plan_id: str) -> dict[str, Any]:
    plan = ContextInjectionPlanner().get_plan(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="context_injection_plan_not_found")
    return {"plan_id": plan_id, "trace": [item.model_dump() for item in plan.trace]}


@router.get("/context/plans")
def list_context_plans(limit: int = Query(default=100, ge=1, le=1000)) -> dict[str, Any]:
    return {"status": "ok", "plans": [plan.model_dump() for plan in ContextInjectionPlanner().list_plans(limit=limit)]}
