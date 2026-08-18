from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.rag.retrieval_request import Citation, SourceRef
from aipinho.schemas.rag.vector.contracts import RAGChunk, RAGChunkSource, RAGIngestionRequest


def unique_id(prefix: str = "sprint29") -> str:
    return f"{prefix}_{uuid4().hex}"


def source_ref(*, source_id: str = "source_code_snapshots", ref: str = "src/aipinho/example.py") -> SourceRef:
    return SourceRef(
        source_id=source_id,
        source_type="file",
        ref=ref,
        location=f"{ref}:1-8",
        content_hash="a" * 64,
    )


def citation(*, source_id: str = "source_code_snapshots", ref: str = "src/aipinho/example.py", excerpt: str = "AIpinho uses governed Vector RAG.") -> Citation:
    return Citation(
        citation_type="file_line_range",
        source_ref=source_ref(source_id=source_id, ref=ref),
        excerpt=excerpt,
        line_start=1,
        line_end=8,
    )


def ingestion_request(
    *,
    namespace_id: str = "coder_rag",
    source_type: str = "source_code_snapshots",
    source_id: str | None = None,
    text: str = "AIpinho Vector RAG keeps source citations and role namespaces.",
) -> RAGIngestionRequest:
    sid = source_id or unique_id("source")
    return RAGIngestionRequest(
        namespace_id=namespace_id,
        source_type=source_type,
        source_id=sid,
        text=text,
        source_ref=source_ref(source_id=source_type),
        citation=citation(source_id=source_type, excerpt=text[:120]),
        scope="project",
    )


def chunk(
    *,
    namespace_id: str = "coder_rag",
    source_type: str = "source_code_snapshots",
    text: str = "AIpinho Vector RAG chunk with preserved citation.",
) -> RAGChunk:
    return RAGChunk(
        namespace_id=namespace_id,
        text=text,
        source=RAGChunkSource(
            source_type=source_type,
            source_id=unique_id("source"),
            source_ref=source_ref(source_id=source_type),
            citation=citation(source_id=source_type, excerpt=text[:120]),
        ),
    )
