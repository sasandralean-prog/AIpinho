from __future__ import annotations

from aipinho.services.rag.vector.vector_index_registry import VectorIndexRegistry


class VisionRAGNamespaceService:
    def __init__(self) -> None:
        self.registry = VectorIndexRegistry()

    def list_namespaces(self) -> list[dict[str, object]]:
        return [namespace.model_dump() for namespace in self.registry.list_namespaces(include_disabled=True) if namespace.namespace_id in {"vision_rag", "ocr_rag"}]

    def status(self) -> dict[str, object]:
        namespaces = self.list_namespaces()
        return {"status": "ok" if len(namespaces) == 2 else "degraded", "service": "vision_rag_namespace", "namespaces": namespaces}
