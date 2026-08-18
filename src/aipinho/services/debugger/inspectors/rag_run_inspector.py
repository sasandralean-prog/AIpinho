from __future__ import annotations

from aipinho.services.debugger.inspectors._shared import BaseInspector, finding
from aipinho.services.rag.vector.rag_vector_query_service import RAGVectorQueryService


class RAGRunInspector(BaseInspector):
    target_type = "rag_run"

    def inspect(self, query_id: str):
        query = RAGVectorQueryService().get_query(query_id)
        if query is None:
            return self.missing(query_id)
        hits = query.get("hits", []) if isinstance(query.get("hits", []), list) else []
        findings = []
        if any("legacy" in str(item).lower() for item in [query.get("namespace_ids"), query.get("metadata")]):
            findings.append(finding("legacy_vectorstore_used", "Legacy vectorstore reference found in RAG run"))
        for hit in hits:
            if isinstance(hit, dict) and not hit.get("citation"):
                findings.append(finding("rag_hit_without_citation", "RAG hit without citation"))
        if not query.get("trace_id"):
            findings.append(finding("rag_run_without_trace", "RAG query has no trace_id", "high"))
        return self.result(query_id, {"query": query}, findings, summary="RAG query inspected")
