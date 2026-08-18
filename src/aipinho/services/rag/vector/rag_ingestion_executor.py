from __future__ import annotations

import json

from aipinho.core.paths import PATHS
from aipinho.schemas.rag.vector.contracts import EmbeddingRequest, RAGChunk, RAGIngestionResult, VectorRAGAudit
from aipinho.services.rag.vector.embedding_provider_service import EmbeddingProviderService
from aipinho.services.rag.vector.rag_chunk_validator import RAGChunkValidator
from aipinho.services.rag.vector.rag_ingestion_approval_service import RAGIngestionApprovalService
from aipinho.services.rag.vector.rag_ingestion_preview_service import RAGIngestionPreviewService
from aipinho.services.rag.vector.vector_index_registry import VectorIndexRegistry
from aipinho.services.rag.vector.vector_index_store import VectorIndexStore
from aipinho.services.rag.vector.vector_rag_audit_service import VectorRAGAuditService
from aipinho.services.rag.vector.vector_rag_trace_service import VectorRAGTraceService


class RAGIngestionExecutor:
    def __init__(self) -> None:
        self.preview_service = RAGIngestionPreviewService()
        self.approvals = RAGIngestionApprovalService(self.preview_service)
        self.registry = VectorIndexRegistry()
        self.store = VectorIndexStore()
        self.embedder = EmbeddingProviderService()
        self.validator = RAGChunkValidator()
        self.trace = VectorRAGTraceService()
        self.audit = VectorRAGAuditService()
        self.result_dir = PATHS.project_root / "data" / "runtime" / "rag_ingestions" / "results"

    def execute(self, *, preview_id: str, approval_id: str) -> RAGIngestionResult:
        stored = self.preview_service.get_preview(preview_id)
        approval = self.approvals.get_approval(approval_id)
        if not stored:
            return self._blocked("unknown", "unknown", approval_id, ["preview_not_found"])
        if not approval or approval.get("status") != "approved":
            namespace_id = stored["preview"].get("namespace_id", "unknown")
            return self._blocked(stored["preview"].get("ingestion_id", "unknown"), namespace_id, approval_id, ["approved_approval_required"])
        preview = stored["preview"]
        namespace = self.registry.get_namespace(preview["namespace_id"])
        if not namespace:
            return self._blocked(preview["ingestion_id"], preview["namespace_id"], approval_id, ["unknown_namespace"])
        chunks = [RAGChunk.model_validate(item) for item in preview.get("chunks", [])]
        validation = self.validator.validate_many(chunks)
        if not validation["valid"]:
            return self._blocked(preview["ingestion_id"], preview["namespace_id"], approval_id, list(validation.get("blocked_reasons", [])))
        embedding = self.embedder.embed(EmbeddingRequest(model_id=namespace.embedding_model, chunks=chunks))
        if embedding.status != "ok":
            return self._blocked(preview["ingestion_id"], preview["namespace_id"], approval_id, embedding.blocked_reasons)
        index = self.store.save_chunks(namespace, chunks, embedding.embeddings)
        trace_id = preview.get("trace_id") or self.trace.create("Vector RAG ingestion execute")
        result = RAGIngestionResult(ingestion_id=preview["ingestion_id"], status="indexed", namespace_id=namespace.namespace_id, approval_id=approval_id, chunks_indexed=len(chunks), embeddings_saved=len(embedding.embeddings), citations_saved=len(chunks), manifest_path=index.manifest_path, trace_id=trace_id, warnings=embedding.warnings)
        self.trace.record(trace_id, event_type="ingest_execute", status="indexed", summary="Ingestion executed", data=result.model_dump())
        self.audit.record(VectorRAGAudit(event_type="ingest_execute", status="indexed", namespace_id=namespace.namespace_id, ingestion_id=result.ingestion_id, data={"chunks": len(chunks)}))
        self._save(result)
        return result

    def get_result(self, ingestion_id: str) -> dict | None:
        path = self.result_dir / f"{ingestion_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _blocked(self, ingestion_id: str, namespace_id: str, approval_id: str | None, reasons: list[str]) -> RAGIngestionResult:
        return RAGIngestionResult(ingestion_id=ingestion_id, status="blocked", namespace_id=namespace_id, approval_id=approval_id, blocked_reasons=list(dict.fromkeys(reasons)))

    def _save(self, result: RAGIngestionResult) -> None:
        self.result_dir.mkdir(parents=True, exist_ok=True)
        (self.result_dir / f"{result.ingestion_id}.json").write_text(json.dumps(result.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "rag_ingestion_executor", "approval_required": True}
