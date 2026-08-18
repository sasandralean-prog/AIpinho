from aipinho.services.rag.vector.rag_ingestion_approval_service import RAGIngestionApprovalService
from aipinho.services.rag.vector.rag_ingestion_preview_service import RAGIngestionPreviewService

from vector_rag_test_helpers import ingestion_request


def test_rag_ingestion_approval_does_not_execute_ingestion():
    preview_service = RAGIngestionPreviewService()
    approval_service = RAGIngestionApprovalService(preview_service)
    preview = preview_service.preview(ingestion_request())

    created = approval_service.create_approval(preview.preview_id)
    assert created["status"] == "ok"
    assert created["ingested"] is False

    approved = approval_service.approve(created["approval"]["approval_id"])
    assert approved["status"] == "ok"
    assert approved["ingested"] is False
    assert approved["approval"]["execution_status"] == "not_executed"
