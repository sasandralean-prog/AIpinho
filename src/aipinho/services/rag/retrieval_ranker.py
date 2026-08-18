from __future__ import annotations

from aipinho.schemas.rag.retrieval_request import RetrievalHit, RetrievalQuery


class RetrievalRanker:
    def rank(self, hits: list[RetrievalHit], query: RetrievalQuery) -> list[RetrievalHit]:
        tokens = set(query.tokens)
        phrase = query.normalized
        ranked: list[RetrievalHit] = []
        for hit in hits:
            text = f"{hit.title} {hit.excerpt}".lower()
            score = 0.0
            if phrase and phrase in text:
                score += 3.0
            score += len(tokens.intersection(set(text.split()))) * 1.0
            if any(token in hit.title.lower() for token in tokens):
                score += 1.5
            if hit.citation and hit.citation.evidence_id:
                score += 2.0
            if hit.source_id == "curated_memory":
                score += 0.5
            hit.score = round(score, 4)
            ranked.append(hit)
        return sorted(ranked, key=lambda item: (-item.score, item.source_id, item.title, item.hit_id))

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "retrieval_ranker", "algorithm": "weighted_lexical", "embeddings_enabled": False, "llm_reranker_enabled": False}
