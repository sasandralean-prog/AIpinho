from __future__ import annotations

from aipinho.schemas.evals.contracts import EvalRequest
from aipinho.services.evals._shared import BaseEvaluator, finding


class RAGEvaluationService(BaseEvaluator):
    evaluator = "rag"

    def evaluate(self, request: EvalRequest):
        payload = request.payload
        findings = []
        hits = payload.get("hits", []) or []
        if payload.get("legacy_vectorstore_used"):
            findings.append(finding("legacy_vectorstore_used", "Legacy vectorstore used in RAG"))
        if payload.get("expected_namespace") and payload.get("namespace_id") != payload.get("expected_namespace"):
            findings.append(finding("rag_namespace_mismatch", "RAG namespace does not match expected role namespace"))
        for hit in hits:
            if isinstance(hit, dict) and not hit.get("citation"):
                findings.append(finding("rag_hit_without_citation", "RAG hit without citation"))
        return self.make_result(request, findings, {"hit_count": len(hits)})
