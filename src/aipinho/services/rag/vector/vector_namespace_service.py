from __future__ import annotations

from aipinho.schemas.rag.vector.contracts import VectorNamespace
from aipinho.services.rag.vector.vector_index_registry import VectorIndexRegistry


class VectorNamespaceService:
    def __init__(self, registry: VectorIndexRegistry | None = None) -> None:
        self.registry = registry or VectorIndexRegistry()

    def list_namespaces(self, *, include_disabled: bool = True) -> list[VectorNamespace]:
        return self.registry.list_namespaces(include_disabled=include_disabled)

    def get_namespace(self, namespace_id: str) -> VectorNamespace | None:
        return self.registry.get_namespace(namespace_id)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "vector_namespace", "registry": self.registry.status()}
