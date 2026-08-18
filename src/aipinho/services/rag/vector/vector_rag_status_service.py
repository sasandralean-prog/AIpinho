from __future__ import annotations

from aipinho.schemas.rag.vector.contracts import VectorRAGStatus
from aipinho.services.rag.vector.embedding_runtime_gate import EmbeddingRuntimeGate
from aipinho.services.rag.vector.reranker_runtime_gate import RerankerRuntimeGate
from aipinho.services.rag.vector.vector_index_registry import VectorIndexRegistry
from aipinho.services.rag.vector.vector_index_store import VectorIndexStore


class VectorRAGStatusService:
    def __init__(self) -> None:
        self.registry = VectorIndexRegistry()
        self.store = VectorIndexStore()
        self.embedding_gate = EmbeddingRuntimeGate()
        self.reranker_gate = RerankerRuntimeGate()

    def status_model(self) -> VectorRAGStatus:
        namespaces = []
        for namespace in self.registry.list_namespaces(include_disabled=True):
            index = self.store.index(namespace)
            namespaces.append({**namespace.model_dump(), "index": index.model_dump()})
        embedding = self.embedding_gate.decide()
        reranker = self.reranker_gate.decide()
        warnings = [*list(embedding.get("warnings", [])), *list(reranker.get("warnings", []))]
        blocked = [*list(embedding.get("blocked_reasons", [])), *list(reranker.get("blocked_reasons", []))]
        return VectorRAGStatus(
            enabled=True,
            embedding_runtime_enabled=True,
            reranker_runtime_enabled=True,
            embedding_model=str(embedding.get("model_id", "qwen3_embedding_4b_q5_k_m")),
            reranker_model=str(reranker.get("model_id", "qwen3_reranker_4b_q5_k_m")),
            legacy_vectorstore_enabled=False,
            auto_ingest_enabled=False,
            vision_runtime_enabled=False,
            ocr_runtime_enabled=False,
            namespaces=namespaces,
            warnings=list(dict.fromkeys(warnings)),
            blocked_reasons=list(dict.fromkeys(blocked)),
        )

    def status(self) -> dict[str, object]:
        model = self.status_model()
        return {"status": "ok" if not model.blocked_reasons else "degraded", "service": "vector_rag", **model.model_dump()}

