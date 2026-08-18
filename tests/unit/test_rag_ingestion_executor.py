from aipinho.services.rag.vector.rag_ingestion_approval_service import RAGIngestionApprovalService
from aipinho.services.rag.vector.rag_ingestion_executor import RAGIngestionExecutor
from aipinho.services.rag.vector.rag_ingestion_preview_service import RAGIngestionPreviewService

from vector_rag_test_helpers import ingestion_request


def test_rag_ingestion_executor_requires_approved_preview_before_indexing():
    preview_service = RAGIngestionPreviewService()
    approval_service = RAGIngestionApprovalService(preview_service)
    preview = preview_service.preview(ingestion_request(text="Executor indexes only approved cited chunks."))

    pending = approval_service.create_approval(preview.preview_id)["approval"]
    blocked = RAGIngestionExecutor().execute(preview_id=preview.preview_id, approval_id=pending["approval_id"])
    assert blocked.status == "blocked"
    assert "approved_approval_required" in blocked.blocked_reasons

    approval_service.approve(pending["approval_id"])
    result = RAGIngestionExecutor().execute(preview_id=preview.preview_id, approval_id=pending["approval_id"])
    assert result.status == "indexed"
    assert result.chunks_indexed > 0
    assert result.embeddings_saved == result.chunks_indexed
