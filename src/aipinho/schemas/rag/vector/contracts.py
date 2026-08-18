from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.rag.retrieval_request import Citation, RetrievalContextBundle, SourceRef


VectorNamespaceType = Literal["global", "role"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class VectorNamespace(AIpinhoModel):
    namespace_id: str
    namespace_type: VectorNamespaceType
    enabled: bool = True
    role_id: str | None = None
    path: str
    description: str = ""
    allowed_sources: list[str] = Field(default_factory=list)
    embedding_model: str = "qwen3_embedding_4b_q5_k_m"
    reranker_model: str = "qwen3_reranker_4b_q5_k_m"
    disabled_until_sprint: int | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class VectorIndex(AIpinhoModel):
    namespace_id: str
    path: str
    manifest_path: str | None = None
    chunk_store_path: str | None = None
    embedding_store_path: str | None = None
    citation_store_path: str | None = None
    chunk_count: int = 0
    embedding_count: int = 0
    citation_count: int = 0
    embedding_model: str = "qwen3_embedding_4b_q5_k_m"
    reranker_model: str = "qwen3_reranker_4b_q5_k_m"
    status: str = "missing"
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class VectorNamespacePolicy(AIpinhoModel):
    namespace_id: str
    allowed: bool
    status: str
    role_id: str | None = None
    source_type: str | None = None
    path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class RAGChunkSource(AIpinhoModel):
    source_type: str
    source_id: str
    source_ref: SourceRef
    citation: Citation
    scope: str = "project"
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGChunk(AIpinhoModel):
    chunk_id: str = Field(default_factory=lambda: f"rag_chunk_{uuid4().hex}")
    namespace_id: str
    text: str
    source: RAGChunkSource
    embedding: list[float] = Field(default_factory=list)
    content_hash: str | None = None
    created_at: str = Field(default_factory=utc_now)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class EmbeddingRequest(AIpinhoModel):
    model_id: str = "qwen3_embedding_4b_q5_k_m"
    chunks: list[RAGChunk] = Field(default_factory=list)
    purpose: str = "rag_embedding"
    include_trace: bool = True


class EmbeddingResult(AIpinhoModel):
    status: str
    model_id: str = "qwen3_embedding_4b_q5_k_m"
    embeddings: dict[str, list[float]] = Field(default_factory=dict)
    real_runtime_attempted: bool = False
    deterministic_fallback_used: bool = True
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class RAGVectorHit(AIpinhoModel):
    hit_id: str = Field(default_factory=lambda: f"vector_hit_{uuid4().hex}")
    namespace_id: str
    chunk_id: str
    text: str
    score: float = 0.0
    source_ref: SourceRef
    citation: Citation
    metadata: dict[str, Any] = Field(default_factory=dict)


class RerankRequest(AIpinhoModel):
    query: str
    hits: list[RAGVectorHit] = Field(default_factory=list)
    model_id: str = "qwen3_reranker_4b_q5_k_m"
    top_k: int = 5
    include_trace: bool = True


class RerankResult(AIpinhoModel):
    status: str
    model_id: str = "qwen3_reranker_4b_q5_k_m"
    hits: list[RAGVectorHit] = Field(default_factory=list)
    reranked: bool = False
    real_runtime_attempted: bool = False
    deterministic_fallback_used: bool = True
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class RAGIngestionRequest(AIpinhoModel):
    namespace_id: str
    source_type: str
    source_id: str
    text: str = ""
    source_ref: SourceRef | None = None
    citation: Citation | None = None
    scope: str = "project"
    metadata: dict[str, Any] = Field(default_factory=dict)
    include_trace: bool = True


class RAGIngestionPreview(AIpinhoModel):
    ingestion_id: str = Field(default_factory=lambda: f"rag_ingestion_{uuid4().hex}")
    preview_id: str = Field(default_factory=lambda: f"rag_preview_{uuid4().hex}")
    status: str
    namespace_id: str
    source_type: str
    source_id: str
    source_hash: str | None = None
    chunks: list[RAGChunk] = Field(default_factory=list)
    chunk_count: int = 0
    approval_required: bool = True
    would_write_index: bool = False
    trace_id: str | None = None
    created_at: str = Field(default_factory=utc_now)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class RAGIngestionResult(AIpinhoModel):
    ingestion_id: str
    status: str
    namespace_id: str
    approval_id: str | None = None
    chunks_indexed: int = 0
    embeddings_saved: int = 0
    citations_saved: int = 0
    manifest_path: str | None = None
    trace_id: str | None = None
    created_at: str = Field(default_factory=utc_now)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class RAGQueryRequest(AIpinhoModel):
    query_id: str = Field(default_factory=lambda: f"rag_query_{uuid4().hex}")
    query: str
    namespace_id: str | None = None
    role_id: str | None = None
    top_k: int = 5
    use_global_context: bool = True
    include_context_bundle: bool = True
    max_context_chars: int = 30000
    include_trace: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class RAGQueryResult(AIpinhoModel):
    query_id: str
    status: str
    query: str
    namespace_ids: list[str] = Field(default_factory=list)
    hits: list[RAGVectorHit] = Field(default_factory=list)
    context_bundle: RetrievalContextBundle | None = None
    trace_id: str | None = None
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


class RoleRAGPolicy(AIpinhoModel):
    role_id: str
    allowed_namespaces: list[str] = Field(default_factory=list)
    include_global: bool = True


class RoleRAGContext(AIpinhoModel):
    role_id: str
    query: str
    result: RAGQueryResult
    safe_for_prompt_assembly: bool = False


class GlobalRAGContext(AIpinhoModel):
    query: str
    result: RAGQueryResult
    supporting_context: bool = True


class VectorRAGTrace(AIpinhoModel):
    trace_id: str
    events: list[dict[str, Any]] = Field(default_factory=list)


class VectorRAGAudit(AIpinhoModel):
    event_id: str = Field(default_factory=lambda: f"vector_rag_audit_{uuid4().hex}")
    event_type: str
    status: str
    namespace_id: str | None = None
    source_id: str | None = None
    query_id: str | None = None
    ingestion_id: str | None = None
    created_at: str = Field(default_factory=utc_now)
    data: dict[str, Any] = Field(default_factory=dict)


class VectorRAGStatus(AIpinhoModel):
    enabled: bool = True
    mode: str = "governed_vector_rag"
    embedding_runtime_enabled: bool = True
    reranker_runtime_enabled: bool = True
    embedding_model: str = "qwen3_embedding_4b_q5_k_m"
    reranker_model: str = "qwen3_reranker_4b_q5_k_m"
    legacy_vectorstore_enabled: bool = False
    auto_ingest_enabled: bool = False
    vision_runtime_enabled: bool = False
    ocr_runtime_enabled: bool = False
    role_namespaces_enabled: bool = True
    global_namespace_enabled: bool = True
    namespaces: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
