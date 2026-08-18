from aipinho.services.rag.vector.rag_ingestion_preview_service import RAGIngestionPreviewService

from vector_rag_test_helpers import ingestion_request


def test_rag_ingestion_preview_never_writes_index_and_requires_allowed_source():
    service = RAGIngestionPreviewService()

    preview = service.preview(ingestion_request())

    assert preview.status == "ready"
    assert preview.approval_required is True
    assert preview.would_write_index is False
    assert preview.chunk_count > 0

    blocked = service.preview(ingestion_request(source_type="project_reports"))
    assert blocked.status == "blocked"
    assert "source_not_allowed_for_namespace" in blocked.blocked_reasons
