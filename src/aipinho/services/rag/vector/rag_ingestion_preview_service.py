from __future__ import annotations

import hashlib
import json

from aipinho.core.paths import PATHS
from aipinho.schemas.rag.vector.contracts import RAGIngestionPreview, RAGIngestionRequest, VectorRAGAudit
from aipinho.services.rag.vector.citation_preserving_chunker import CitationPreservingChunker
from aipinho.services.rag.vector.rag_chunk_validator import RAGChunkValidator
from aipinho.services.rag.vector.rag_sensitivity_gate import RAGSensitivityGate
from aipinho.services.rag.vector.vector_index_registry import VectorIndexRegistry
from aipinho.services.rag.vector.vector_namespace_policy_service import VectorNamespacePolicyService
from aipinho.services.rag.vector.vector_rag_audit_service import VectorRAGAuditService
from aipinho.services.rag.vector.vector_rag_trace_service import VectorRAGTraceService


class RAGIngestionPreviewService:
    def __init__(self) -> None:
        self.registry = VectorIndexRegistry()
        self.policy = VectorNamespacePolicyService(self.registry)
        self.chunker = CitationPreservingChunker()
        self.validator = RAGChunkValidator()
        self.sensitivity = RAGSensitivityGate()
        self.trace = VectorRAGTraceService()
        self.audit = VectorRAGAuditService()
        self.store_dir = PATHS.project_root / "data" / "runtime" / "rag_ingestions" / "previews"

    def preview(self, request: RAGIngestionRequest) -> RAGIngestionPreview:
        trace_id = self.trace.create(f"Vector RAG ingest preview for {request.namespace_id}")
        namespace = self.registry.get_namespace(request.namespace_id)
        policy = self.policy.validate(namespace, source_type=request.source_type)
        blocked = list(policy.blocked_reasons)
        sensitivity = self.sensitivity.check(request.text, source_type=request.source_type)
        blocked.extend([str(item) for item in sensitivity.get("blocked_reasons", [])])
        chunks, chunk_errors = self.chunker.chunk(request)
        blocked.extend(chunk_errors)
        validation = self.validator.validate_many(chunks)
        blocked.extend([str(item) for item in validation.get("blocked_reasons", [])])
        blocked = list(dict.fromkeys(blocked))
        status = "ready" if not blocked and chunks else "blocked"
        preview = RAGIngestionPreview(
            status=status,
            namespace_id=request.namespace_id,
            source_type=request.source_type,
            source_id=request.source_id,
            source_hash=hashlib.sha256(request.text.encode("utf-8")).hexdigest() if request.text else None,
            chunks=chunks if status == "ready" else [],
            chunk_count=len(chunks) if status == "ready" else 0,
            approval_required=True,
            would_write_index=False,
            trace_id=trace_id,
            warnings=list(policy.warnings),
            blocked_reasons=blocked,
        )
        self.trace.record(trace_id, event_type="ingest_preview", status=status, summary="Ingest preview completed", data={"namespace_id": request.namespace_id, "chunk_count": preview.chunk_count, "blocked_reasons": blocked})
        self.audit.record(VectorRAGAudit(event_type="ingest_preview", status=status, namespace_id=request.namespace_id, source_id=request.source_id, ingestion_id=preview.ingestion_id, data={"blocked_reasons": blocked}))
        self._save(preview, request)
        return preview

    def get_preview(self, preview_id: str) -> dict | None:
        path = self.store_dir / f"{preview_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, preview: RAGIngestionPreview, request: RAGIngestionRequest) -> None:
        self.store_dir.mkdir(parents=True, exist_ok=True)
        payload = {"preview": preview.model_dump(), "request": request.model_dump()}
        (self.store_dir / f"{preview.preview_id}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "rag_ingestion_preview", "preview_writes_index": False}
