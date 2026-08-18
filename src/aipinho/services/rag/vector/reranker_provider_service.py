from __future__ import annotations

from aipinho.schemas.rag.vector.contracts import RAGVectorHit, RerankRequest, RerankResult
from aipinho.services.rag.vector.config import rag_config
from aipinho.services.rag.vector.llama_server_runtime_service import LlamaServerRuntimeService
from aipinho.services.rag.vector.reranker_runtime_gate import RerankerRuntimeGate


class RerankerProviderService:
    def __init__(self, gate: RerankerRuntimeGate | None = None, runtime: LlamaServerRuntimeService | None = None) -> None:
        self.gate = gate or RerankerRuntimeGate()
        self.runtime = runtime or LlamaServerRuntimeService()
        self.config = rag_config("reranker_policy.yaml")

    def rerank(self, request: RerankRequest) -> RerankResult:
        gate = self.gate.decide(request.model_id)
        if not gate["allowed"]:
            return RerankResult(status="blocked", model_id=request.model_id, hits=[], blocked_reasons=list(gate.get("blocked_reasons", [])), warnings=list(gate.get("warnings", [])))
        valid_hits = [hit for hit in request.hits if hit.citation and hit.source_ref]
        runtime_result = self.runtime.rerank(
            query=request.query,
            documents=[hit.text for hit in valid_hits],
            model_id=request.model_id,
            top_k=request.top_k,
        )
        warnings = list(dict.fromkeys([*list(gate.get("warnings", [])), *(runtime_result.warnings or [])]))
        if runtime_result.status == "ok" and isinstance(runtime_result.data, list):
            indexed_scores = [(index, score) for index, score in runtime_result.data if 0 <= index < len(valid_hits)]
            ordered_hits = [
                valid_hits[index].model_copy(update={"score": float(score)})
                for index, score in sorted(indexed_scores, key=lambda item: item[1], reverse=True)
            ][: max(0, request.top_k)]
            return RerankResult(
                status="ok",
                model_id=request.model_id,
                hits=ordered_hits,
                reranked=True,
                real_runtime_attempted=True,
                deterministic_fallback_used=False,
                warnings=warnings,
            )
        if not self._fallback_allowed():
            return RerankResult(
                status="error",
                model_id=request.model_id,
                hits=[],
                reranked=False,
                real_runtime_attempted=True,
                deterministic_fallback_used=False,
                warnings=warnings,
                blocked_reasons=list(runtime_result.blocked_reasons or []),
            )
        query_tokens = {token.lower() for token in request.query.split() if token.strip()}
        def score(hit: RAGVectorHit) -> float:
            text_tokens = {token.lower().strip(".,:;") for token in hit.text.split()}
            overlap = len(query_tokens & text_tokens)
            return hit.score + overlap
        reranked = sorted(valid_hits, key=score, reverse=True)[: max(0, request.top_k)]
        return RerankResult(
            status="ok",
            model_id=request.model_id,
            hits=reranked,
            reranked=True,
            real_runtime_attempted=True,
            deterministic_fallback_used=True,
            warnings=list(dict.fromkeys([*warnings, "reranker_runtime_fallback_used"])),
        )

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "reranker_provider",
            "model_id": "qwen3_reranker_4b_q5_k_m",
            "chat_use_enabled": False,
            "runtime": self.runtime.status().get("reranker", {}),
            "deterministic_fallback": "lexical_overlap" if self._fallback_allowed() else "disabled",
        }

    def _fallback_allowed(self) -> bool:
        policy = self.config.get("reranker", {}) if isinstance(self.config.get("reranker", {}), dict) else {}
        return bool(policy.get("allow_deterministic_fallback_when_runtime_unavailable", True))
