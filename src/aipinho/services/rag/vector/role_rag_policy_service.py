from __future__ import annotations

from aipinho.services.rag.vector.config import rag_config


class RoleRAGPolicyService:
    def __init__(self, config: dict | None = None) -> None:
        self.config = config or rag_config("role_rag_policy.yaml")

    def allowed_namespaces(self, role_id: str) -> list[str]:
        access = self.config.get("role_access", {}) if isinstance(self.config.get("role_access", {}), dict) else {}
        return [str(item) for item in access.get(role_id, []) or []]

    def can_access(self, role_id: str, namespace_id: str) -> bool:
        return namespace_id in self.allowed_namespaces(role_id)

    def status(self) -> dict[str, object]:
        access = self.config.get("role_access", {}) if isinstance(self.config.get("role_access", {}), dict) else {}
        return {"status": "ok", "service": "role_rag_policy", "roles": sorted(access), "cross_role_namespace_access_enabled": False}
