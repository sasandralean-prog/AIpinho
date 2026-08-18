from __future__ import annotations

from aipinho.schemas.rag.retrieval_request import Citation, SourceRef
from aipinho.schemas.rag.vector.contracts import RAGIngestionPreview, RAGIngestionRequest
from aipinho.schemas.vision.contracts import OCRResult, VisionAnalysisResult, VisionRAGIngestionRequest
from aipinho.services.rag.vector.rag_ingestion_preview_service import RAGIngestionPreviewService


class VisionRAGIngestionPreviewService:
    def __init__(self) -> None:
        self.preview_service = RAGIngestionPreviewService()

    def preview(self, request: VisionRAGIngestionRequest) -> RAGIngestionPreview:
        if request.result is None:
            return self.preview_service.preview(
                RAGIngestionRequest(namespace_id=request.target_namespace, source_type="missing_visual_result", source_id="missing", text="")
            )
        vector_request = self._to_vector_request(request.result, request.target_namespace)
        return self.preview_service.preview(vector_request)

    def _to_vector_request(self, result: VisionAnalysisResult | OCRResult, target_namespace: str) -> RAGIngestionRequest:
        if isinstance(result, VisionAnalysisResult):
            if not result.evidence:
                return RAGIngestionRequest(namespace_id=target_namespace, source_type="visual_evidence", source_id=result.run_id, text="")
            evidence = result.evidence[0]
            citation = evidence.citation
            source_ref = SourceRef(
                source_id=evidence.evidence_id,
                source_type="visual_evidence",
                ref=evidence.source_ref.path or evidence.source_ref.file_name or evidence.source_ref.image_id,
                location=str(citation.region.model_dump()) if citation.region else "whole_image",
                content_hash=evidence.source_ref.content_hash,
            )
            return RAGIngestionRequest(
                namespace_id=target_namespace,
                source_type="visual_evidence",
                source_id=evidence.evidence_id,
                text=evidence.summary,
                source_ref=source_ref,
                citation=Citation(citation_type="evidence_id", source_ref=source_ref, excerpt=citation.summary, evidence_id=evidence.evidence_id),
                metadata={"vision_run_id": result.run_id, "confidence": evidence.confidence, "raw_blob_included": False},
            )
        if not result.text_blocks:
            return RAGIngestionRequest(namespace_id=target_namespace, source_type="ocr_text_block", source_id=result.run_id, text="")
        block = result.text_blocks[0]
        citation = block.citation
        if citation is None:
            return RAGIngestionRequest(namespace_id=target_namespace, source_type="ocr_text_block", source_id=block.block_id, text=block.text)
        source_ref = SourceRef(
            source_id=block.block_id,
            source_type="ocr_text_block",
            ref=citation.source_ref.path or citation.source_ref.file_name or citation.source_ref.image_id,
            location=f"page={block.page or 1}; region={citation.region.model_dump() if citation.region else 'whole_page'}",
            content_hash=citation.source_ref.content_hash,
        )
        return RAGIngestionRequest(
            namespace_id=target_namespace,
            source_type="ocr_text_block",
            source_id=block.block_id,
            text=block.text,
            source_ref=source_ref,
            citation=Citation(citation_type="evidence_id", source_ref=source_ref, excerpt=citation.excerpt, evidence_id=block.block_id),
            metadata={"ocr_run_id": result.run_id, "confidence": block.confidence, "raw_blob_included": False},
        )

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "vision_rag_ingestion_preview", "would_write_index": False, "approval_required": True}


