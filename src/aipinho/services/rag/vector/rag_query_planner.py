from __future__ import annotations

from aipinho.schemas.rag.vector.contracts import RAGQueryRequest
from aipinho.services.rag.vector.role_rag_policy_service import RoleRAGPolicyService
from aipinho.services.rag.vector.vector_index_registry import VectorIndexRegistry
from aipinho.services.rag.vector.vector_namespace_policy_service import VectorNamespacePolicyService


class RAGQueryPlanner:
    def __init__(self) -> None:
        self.registry = VectorIndexRegistry()
        self.policy = VectorNamespacePolicyService(self.registry)
        self.role_policy = RoleRAGPolicyService()

    def plan(self, request: RAGQueryRequest) -> dict[str, object]:
        blocked: list[str] = []
        namespaces: list[str] = []
        if request.namespace_id:
            namespaces.append(request.namespace_id)
        elif request.role_id:
            namespaces.extend([item for item in self.role_policy.allowed_namespaces(request.role_id) if item != "global_ecosystem"])
        else:
            namespaces.append("global_ecosystem")
        if request.use_global_context and "global_ecosystem" not in namespaces:
            namespaces.append("global_ecosystem")
        for namespace_id in namespaces:
            namespace = self.registry.get_namespace(namespace_id)
            role_for_check = request.role_id if namespace and namespace.namespace_type == "role" else None
            decision = self.policy.validate(namespace, role_id=role_for_check)
            if not decision.allowed:
                blocked.extend(decision.blocked_reasons)
            if request.role_id and namespace_id not in self.role_policy.allowed_namespaces(request.role_id):
                blocked.append("cross_role_namespace_blocked")
        return {"status": "ok" if not blocked else "blocked", "namespace_ids": list(dict.fromkeys(namespaces)), "blocked_reasons": list(dict.fromkeys(blocked))}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "rag_query_planner"}
