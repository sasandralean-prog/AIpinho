from __future__ import annotations

from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.rag.vector.contracts import VectorNamespace, VectorNamespacePolicy
from aipinho.services.rag.vector.vector_index_registry import VectorIndexRegistry


class VectorNamespacePolicyService:
    def __init__(self, registry: VectorIndexRegistry | None = None) -> None:
        self.registry = registry or VectorIndexRegistry()

    def validate(self, namespace: VectorNamespace | None, *, source_type: str | None = None, role_id: str | None = None) -> VectorNamespacePolicy:
        blocked: list[str] = []
        warnings: list[str] = []
        if namespace is None:
            return VectorNamespacePolicy(namespace_id="unknown", allowed=False, status="blocked", blocked_reasons=["unknown_namespace"])
        if not namespace.enabled:
            blocked.append("namespace_disabled")
        if self.registry.is_legacy_path(namespace.path):
            blocked.append("legacy_vectorstore_blocked")
        path = (PATHS.project_root / namespace.path).resolve()
        governed = self.registry.governed_root().resolve()
        if not str(path).lower().startswith(str(governed).lower()):
            blocked.append("path_outside_governed_vectorstore")
        if source_type and source_type not in namespace.allowed_sources:
            blocked.append("source_not_allowed_for_namespace")
        if role_id and namespace.namespace_type == "role" and namespace.role_id != role_id:
            blocked.append("cross_role_namespace_blocked")
        return VectorNamespacePolicy(
            namespace_id=namespace.namespace_id,
            allowed=not blocked,
            status="ok" if not blocked else "blocked",
            role_id=role_id,
            source_type=source_type,
            path=str(path),
            warnings=warnings,
            blocked_reasons=blocked,
        )

    def ensure_governed_path(self, path: Path) -> bool:
        governed = self.registry.governed_root().resolve()
        return str(path.resolve()).lower().startswith(str(governed).lower()) and not self.registry.is_legacy_path(path)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "vector_namespace_policy", "legacy_blocked": True, "governed_root": str(self.registry.governed_root())}
