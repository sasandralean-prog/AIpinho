from __future__ import annotations

import hashlib

from aipinho.schemas.rag.vector.contracts import RAGChunk, RAGChunkSource, RAGIngestionRequest
from aipinho.services.rag.vector.config import rag_config


class CitationPreservingChunker:
    def __init__(self, config: dict | None = None) -> None:
        self.config = config or rag_config("chunking_policy.yaml")

    def chunk(self, request: RAGIngestionRequest) -> tuple[list[RAGChunk], list[str]]:
        if request.source_ref is None or request.citation is None:
            return [], ["missing_source_ref_or_citation"]
        policy = self.config.get("chunking", {}) if isinstance(self.config.get("chunking", {}), dict) else {}
        max_chars = int(policy.get("max_chunk_chars", 900))
        text = request.text.strip()
        if not text:
            return [], ["empty_source_text"]
        chunks: list[RAGChunk] = []
        for index in range(0, len(text), max_chars):
            part = text[index : index + max_chars]
            content_hash = hashlib.sha256(part.encode("utf-8")).hexdigest()
            chunks.append(
                RAGChunk(
                    namespace_id=request.namespace_id,
                    text=part,
                    source=RAGChunkSource(source_type=request.source_type, source_id=request.source_id, source_ref=request.source_ref, citation=request.citation, scope=request.scope, metadata={"chunk_index": index // max_chars}),
                    content_hash=content_hash,
                )
            )
        return chunks, []

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "citation_preserving_chunker", "citation_required": True}
