from __future__ import annotations

from aipinho.services.rag.vector.rag_chunk_validator import RAGChunkValidator
from aipinho.services.rag.vector.vector_index_registry import VectorIndexRegistry
from aipinho.services.rag.vector.vector_index_store import VectorIndexStore


class RAGIndexDoctorService:
    def __init__(self) -> None:
        self.registry = VectorIndexRegistry()
        self.store = VectorIndexStore()
        self.validator = RAGChunkValidator()

    def doctor(self, namespace_id: str) -> dict[str, object]:
        namespace = self.registry.get_namespace(namespace_id)
        if namespace is None:
            return {"status": "blocked", "namespace_id": namespace_id, "blocked_reasons": ["unknown_namespace"]}
        if not namespace.enabled:
            return {"status": "blocked", "namespace_id": namespace_id, "blocked_reasons": ["namespace_disabled"]}
        index = self.store.index(namespace)
        chunks = self.store.load_chunks(namespace)
        validation = self.validator.validate_many(chunks)
        blocked = list(validation.get("blocked_reasons", []))
        if index.status == "missing":
            return {"status": "missing", "namespace_id": namespace_id, "index": index.model_dump(), "blocked_reasons": []}
        if not validation["valid"]:
            return {"status": "blocked", "namespace_id": namespace_id, "index": index.model_dump(), "blocked_reasons": blocked}
        return {"status": "healthy", "namespace_id": namespace_id, "index": index.model_dump(), "blocked_reasons": []}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "rag_index_doctor"}
