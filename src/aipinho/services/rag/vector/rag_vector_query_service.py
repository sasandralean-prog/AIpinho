from __future__ import annotations

import json
import math
import re

from aipinho.core.paths import PATHS
from aipinho.schemas.rag.retrieval_request import RetrievalBudget, RetrievalContextBundle, RetrievalHit, RetrievalQuery, RetrievalRequest
from aipinho.schemas.rag.vector.contracts import RAGQueryRequest, RAGQueryResult, RAGVectorHit, RerankRequest, VectorRAGAudit
from aipinho.services.rag.retrieval_context_builder import RetrievalContextBuilder
from aipinho.services.rag.vector.embedding_provider_service import EmbeddingProviderService
from aipinho.services.rag.vector.rag_citation_validator import RAGCitationValidator
from aipinho.services.rag.vector.rag_query_planner import RAGQueryPlanner
from aipinho.services.rag.vector.rag_rerank_service import RAGRerankService
from aipinho.services.rag.vector.vector_index_registry import VectorIndexRegistry
from aipinho.services.rag.vector.vector_index_store import VectorIndexStore
from aipinho.services.rag.vector.vector_rag_audit_service import VectorRAGAuditService
from aipinho.services.rag.vector.vector_rag_trace_service import VectorRAGTraceService


class RAGVectorQueryService:
    def __init__(self) -> None:
        self.registry = VectorIndexRegistry()
        self.store = VectorIndexStore()
        self.planner = RAGQueryPlanner()
        self.embedder = EmbeddingProviderService()
        self.reranker = RAGRerankService()
        self.citations = RAGCitationValidator()
        self.context_builder = RetrievalContextBuilder()
        self.trace = VectorRAGTraceService()
        self.audit = VectorRAGAuditService()
        self.result_dir = PATHS.project_root / "data" / "runtime" / "rag_queries"

    def query(self, request: RAGQueryRequest) -> RAGQueryResult:
        trace_id = self.trace.create(f"Vector RAG query {request.query_id}")
        plan = self.planner.plan(request)
        if plan["status"] == "blocked":
            return self._result(request, "blocked", [], trace_id, blocked_reasons=list(plan.get("blocked_reasons", [])))
        query_embedding = self.embedder.embed_text(request.query)
        hits: list[RAGVectorHit] = []
        for namespace_id in plan["namespace_ids"]:
            namespace = self.registry.get_namespace(str(namespace_id))
            if not namespace or not namespace.enabled:
                continue
            chunks = self.store.load_chunks(namespace)
            embeddings = self._load_embeddings(namespace)
            for chunk in chunks:
                embedding = embeddings.get(chunk.chunk_id) or self.embedder.embed_text(chunk.text)
                vector_score = self._similarity(query_embedding, embedding)
                lexical_score = self._lexical_score(request.query, chunk.text)
                score = round((0.55 * vector_score) + (0.45 * lexical_score), 6)
                if score <= 0:
                    continue
                hits.append(RAGVectorHit(namespace_id=namespace.namespace_id, chunk_id=chunk.chunk_id, text=chunk.text, score=score, source_ref=chunk.source.source_ref, citation=chunk.source.citation))
        hits = sorted(hits, key=lambda item: item.score, reverse=True)[: max(1, request.top_k * 3)]
        if not hits:
            result = self._result(request, "no_results", [], trace_id)
            self._save(result)
            return result
        citation_check = self.citations.validate_hits(hits)
        if not citation_check["valid"]:
            return self._result(request, "blocked", [], trace_id, blocked_reasons=list(citation_check.get("blocked_reasons", [])))
        reranked = self.reranker.rerank(RerankRequest(query=request.query, hits=hits, top_k=request.top_k))
        final_hits = reranked.hits if reranked.status == "ok" else hits[: request.top_k]
        status = "found"
        if len(self._context_text(final_hits)) > request.max_context_chars:
            status = "partial"
            final_hits = self._trim_hits(final_hits, request.max_context_chars)
        result = self._result(request, status, final_hits, trace_id, namespace_ids=list(plan["namespace_ids"]), warnings=reranked.warnings)
        self.trace.record(trace_id, event_type="vector_query", status=result.status, summary="Vector query completed", data={"namespaces": result.namespace_ids, "hits": len(result.hits)})
        self.audit.record(VectorRAGAudit(event_type="vector_query", status=result.status, query_id=result.query_id, data={"namespaces": result.namespace_ids, "hits": len(result.hits)}))
        self._save(result)
        return result

    def get_query(self, query_id: str) -> dict | None:
        path = self.result_dir / f"{query_id}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def _result(self, request: RAGQueryRequest, status: str, hits: list[RAGVectorHit], trace_id: str, *, namespace_ids: list[str] | None = None, warnings: list[str] | None = None, blocked_reasons: list[str] | None = None) -> RAGQueryResult:
        bundle = self._context_bundle(request, hits, status) if request.include_context_bundle and hits else None
        return RAGQueryResult(query_id=request.query_id, status=status, query=request.query, namespace_ids=namespace_ids or [], hits=hits, context_bundle=bundle, trace_id=trace_id, warnings=warnings or [], blocked_reasons=blocked_reasons or [])

    def _context_bundle(self, request: RAGQueryRequest, hits: list[RAGVectorHit], status: str) -> RetrievalContextBundle:
        retrieval_hits = [
            RetrievalHit(source_id=hit.source_ref.source_id, source_type=hit.source_ref.source_type, title=hit.namespace_id, excerpt=hit.text, score=hit.score, citation=hit.citation, source_ref=hit.source_ref)
            for hit in hits
        ]
        retrieval_request = RetrievalRequest(query=request.query, explicit=True, budget=RetrievalBudget(max_context_chars=request.max_context_chars))
        bundle = self.context_builder.build(retrieval_request, retrieval_hits, retrieval_id=request.query_id, warnings=[] if status != "partial" else ["context_budget_partial"])
        bundle.status = status  # type: ignore[assignment]
        return bundle

    def _load_embeddings(self, namespace) -> dict[str, list[float]]:
        path = self.store.namespace_path(namespace) / "embeddings.json"
        if not path.exists():
            return {}
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _lexical_score(self, query: str, text: str) -> float:
        query_tokens = self._tokens(query)
        text_tokens = self._tokens(text)
        if not query_tokens or not text_tokens:
            return 0.0
        overlap = query_tokens & text_tokens
        if not overlap:
            return 0.0
        precision = len(overlap) / len(query_tokens)
        density = len(overlap) / max(1, min(len(text_tokens), len(query_tokens) * 8))
        return min(1.0, (0.8 * precision) + (0.2 * density))

    def _tokens(self, value: str) -> set[str]:
        stopwords = {"de", "do", "da", "e", "a", "o", "the", "and", "for", "with", "para", "com", "que"}
        return {token.lower() for token in re.findall(r"[A-Za-zÀ-ÿ0-9_]{2,}", value) if token.lower() not in stopwords}

    def _similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right:
            return 0.0
        size = min(len(left), len(right))
        dot = sum(left[index] * right[index] for index in range(size))
        left_norm = math.sqrt(sum(value * value for value in left[:size]))
        right_norm = math.sqrt(sum(value * value for value in right[:size]))
        return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0

    def _context_text(self, hits: list[RAGVectorHit]) -> str:
        return "\n\n".join(hit.text for hit in hits)

    def _trim_hits(self, hits: list[RAGVectorHit], budget: int) -> list[RAGVectorHit]:
        kept: list[RAGVectorHit] = []
        used = 0
        for hit in hits:
            if used + len(hit.text) > budget:
                break
            kept.append(hit)
            used += len(hit.text)
        return kept

    def _save(self, result: RAGQueryResult) -> None:
        self.result_dir.mkdir(parents=True, exist_ok=True)
        (self.result_dir / f"{result.query_id}.json").write_text(json.dumps(result.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "rag_vector_query", "context_bundle_enabled": True}
