from __future__ import annotations

from fastapi import APIRouter

from aipinho.services.rag.vector.role_rag_context_builder import RoleRAGContextBuilder
from aipinho.services.rag.vector.role_rag_policy_service import RoleRAGPolicyService

router = APIRouter(prefix="/api/v1/role-rag", tags=["role-rag"])


@router.get("/status")
def get_role_rag_status() -> dict[str, object]:
    return RoleRAGPolicyService().status()


@router.get("/{role_id}/policy")
def get_role_rag_policy(role_id: str) -> dict[str, object]:
    policy = RoleRAGPolicyService()
    return {"status": "ok", "role_id": role_id, "allowed_namespaces": policy.allowed_namespaces(role_id)}


@router.post("/{role_id}/context")
def build_role_rag_context(role_id: str, payload: dict[str, object]) -> dict[str, object]:
    context = RoleRAGContextBuilder().build(role_id, str(payload.get("query") or ""), top_k=int(payload.get("top_k", 5)), use_global_context=bool(payload.get("use_global_context", True)))
    return {"status": context.result.status, "context": context.model_dump()}
