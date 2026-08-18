from aipinho.schemas.rag.vector.contracts import RAGQueryRequest
from aipinho.services.rag.vector.rag_ingestion_approval_service import RAGIngestionApprovalService
from aipinho.services.rag.vector.rag_ingestion_executor import RAGIngestionExecutor
from aipinho.services.rag.vector.rag_ingestion_preview_service import RAGIngestionPreviewService
from aipinho.services.rag.vector.rag_vector_query_service import RAGVectorQueryService

from vector_rag_test_helpers import ingestion_request


def test_rag_vector_query_returns_cited_hits_after_governed_ingestion():
    text = "Vector RAG query service finds governed cited chunks for coder role."
    preview_service = RAGIngestionPreviewService()
    approval_service = RAGIngestionApprovalService(preview_service)
    preview = preview_service.preview(ingestion_request(text=text))
    approval = approval_service.create_approval(preview.preview_id)["approval"]
    approval_service.approve(approval["approval_id"])
    RAGIngestionExecutor().execute(preview_id=preview.preview_id, approval_id=approval["approval_id"])

    result = RAGVectorQueryService().query(RAGQueryRequest(query="governed cited chunks", role_id="coder"))

    assert result.status in {"found", "partial"}
    assert result.hits
    assert result.hits[0].citation is not None
    assert result.context_bundle is not None
