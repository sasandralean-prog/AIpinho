from __future__ import annotations

from aipinho.services.debugger.inspectors._shared import BaseInspector, finding
from aipinho.services.rag.vector.rag_ingestion_executor import RAGIngestionExecutor
from aipinho.services.rag.vector.rag_ingestion_preview_service import RAGIngestionPreviewService


class RAGIngestionInspector(BaseInspector):
    target_type = "rag_ingestion"

    def inspect(self, ingestion_id: str):
        result = RAGIngestionExecutor().get_result(ingestion_id)
        data = {"ingestion": result}
        findings = []
        if result is None:
            previews = RAGIngestionPreviewService()
            data["preview_lookup"] = "not_found_by_ingestion_id"
            return self.missing(ingestion_id)
        if not result.get("approval_id"):
            findings.append(finding("rag_ingestion_without_approval", "RAG ingestion result has no approval id"))
        return self.result(ingestion_id, data, findings, summary="RAG ingestion inspected")
