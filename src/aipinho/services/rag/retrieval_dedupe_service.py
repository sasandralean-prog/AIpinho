from __future__ import annotations

from aipinho.schemas.rag.retrieval_request import RetrievalHit


class RetrievalDedupeService:
    def dedupe(self, hits: list[RetrievalHit]) -> list[RetrievalHit]:
        by_key: dict[tuple[str, str], RetrievalHit] = {}
        for hit in hits:
            key = (hit.source_id, " ".join(hit.excerpt.lower().split()))
            current = by_key.get(key)
            if current is None or hit.score > current.score:
                by_key[key] = hit
        return list(by_key.values())

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "retrieval_dedupe"}
