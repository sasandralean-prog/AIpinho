from aipinho.schemas.rag.retrieval_request import Citation, SourceRef
from aipinho.schemas.rag.vector.contracts import RAGIngestionRequest
from aipinho.schemas.rag.vector.contracts import RAGQueryRequest
from aipinho.services.rag.vector.rag_ingestion_approval_service import RAGIngestionApprovalService
from aipinho.services.rag.vector.rag_ingestion_executor import RAGIngestionExecutor
from aipinho.services.rag.vector.rag_ingestion_preview_service import RAGIngestionPreviewService
from aipinho.services.rag.vector.rag_query_planner import RAGQueryPlanner
from aipinho.services.rag.vector.rag_vector_query_service import RAGVectorQueryService


def test_governed_vector_rag_flow_enforces_role_namespace_and_citations():
    preview_service = RAGIngestionPreviewService()
    approval_service = RAGIngestionApprovalService(preview_service)
    text = "E2E governed Vector RAG preserves role namespace citations."
    source_ref = SourceRef(source_id="source_code_snapshots", source_type="file", ref="src/aipinho/e2e.py", location="src/aipinho/e2e.py:1-4", content_hash="c" * 64)
    preview = preview_service.preview(
        RAGIngestionRequest(
            namespace_id="coder_rag",
            source_type="source_code_snapshots",
            source_id="e2e_vector_rag_source",
            text=text,
            source_ref=source_ref,
            citation=Citation(citation_type="file_line_range", source_ref=source_ref, excerpt=text, line_start=1, line_end=4),
        )
    )
    approval = approval_service.create_approval(preview.preview_id)["approval"]
    approval_service.approve(approval["approval_id"])

    indexed = RAGIngestionExecutor().execute(preview_id=preview.preview_id, approval_id=approval["approval_id"])
    assert indexed.status == "indexed"

    blocked_cross_role = RAGQueryPlanner().plan(RAGQueryRequest(query="citations", role_id="planner", namespace_id="coder_rag"))
    assert blocked_cross_role["status"] == "blocked"

    found = RAGVectorQueryService().query(RAGQueryRequest(query="role namespace citations", role_id="coder"))
    assert found.status in {"found", "partial"}
    assert found.hits
    assert found.context_bundle.safe_for_prompt_assembly is True
