from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.services.rag.retrieval_source_registry import RetrievalSourceRegistry
from aipinho.services.rag.integration.rag_memory_status_service import RAGMemoryStatusService
from aipinho.services.rag.vector.vector_rag_status_service import VectorRAGStatusService
from aipinho.utils.yaml_loader import inspect_yaml_file


class RetrievalStatusService:
    CONFIGS = [
        "retrieval_policy.yaml",
        "retrieval_source_registry.yaml",
        "retrieval_source_policy.yaml",
        "retrieval_scope_policy.yaml",
        "retrieval_budget_policy.yaml",
        "retrieval_ranking_policy.yaml",
        "retrieval_context_policy.yaml",
        "evidence_bundle_policy.yaml",
        "citation_policy.yaml",
        "retrieval_sensitivity_policy.yaml",
        "retrieval_audit_policy.yaml",
        "retrieval_store_policy.yaml",
        "legacy_rag_block_policy.yaml",
        "vector_rag_policy.yaml",
        "vector_index_registry.yaml",
        "vector_store_policy.yaml",
        "global_rag_policy.yaml",
        "role_rag_policy.yaml",
        "role_rag_namespaces.yaml",
        "embedding_policy.yaml",
        "reranker_policy.yaml",
        "chunking_policy.yaml",
        "rag_ingestion_policy.yaml",
        "rag_ingestion_approval_policy.yaml",
        "rag_query_policy.yaml",
        "rag_namespace_access_policy.yaml",
        "rag_index_doctor_policy.yaml",
        "rag_sensitivity_policy.yaml",
        "rag_audit_policy.yaml",
    ]

    def status(self) -> dict[str, object]:
        root = PATHS.config_root / "rag"
        configs = {name: inspect_yaml_file(root / name, root=PATHS.project_root).__dict__ for name in self.CONFIGS}
        warnings = [f"{name}:{data.get('status')}" for name, data in configs.items() if data.get("status") != "ok"]
        vector_status = VectorRAGStatusService().status()
        return {
            "status": "degraded" if warnings else "ok",
            "service": "governed_retrieval",
            "retrieval_enabled": True,
            "retrieval_mode": "governed_read_only",
            "deterministic_only": True,
            "vectorstore_creation_enabled": True,
            "vector_rag_enabled": bool(vector_status.get("enabled", False)),
            "embeddings_enabled": bool(vector_status.get("embedding_runtime_enabled", False)),
            "reranker_runtime_enabled": bool(vector_status.get("reranker_runtime_enabled", False)),
            "embedding_model": vector_status.get("embedding_model"),
            "reranker_model": vector_status.get("reranker_model"),
            "auto_ingest_enabled": False,
            "legacy_vectorstore_enabled": False,
            "chat_auto_retrieval_enabled": False,
            "prompt_auto_injection_enabled": False,
            "rag_memory_integration": RAGMemoryStatusService().status(),
            "curated_memory_auto_retrieval_enabled": False,
            "curated_memory_explicit_retrieval_enabled": True,
            "workspace_write_enabled": False,
            "memory_write_enabled": False,
            "rag_ingest_enabled": False,
            "vector_rag_ingest_enabled": True,
            "approval_required_for_vector_ingestion": True,
            "vector_rag": vector_status,
            "sources": RetrievalSourceRegistry().status()["sources"],
            "configs": configs,
            "warnings": warnings,
        }
