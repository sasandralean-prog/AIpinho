from __future__ import annotations

import json
from pathlib import Path

from aipinho.core.paths import PATHS
from aipinho.schemas.rag.vector.contracts import RAGChunk, VectorIndex, VectorNamespace
from aipinho.services.rag.vector.vector_namespace_policy_service import VectorNamespacePolicyService


class VectorIndexStore:
    def __init__(self, policy: VectorNamespacePolicyService | None = None) -> None:
        self.policy = policy or VectorNamespacePolicyService()

    def namespace_path(self, namespace: VectorNamespace) -> Path:
        return PATHS.project_root / namespace.path

    def index(self, namespace: VectorNamespace) -> VectorIndex:
        path = self.namespace_path(namespace)
        manifest = path / "manifest.json"
        chunks = self._read_json(path / "chunks.json", [])
        embeddings = self._read_json(path / "embeddings.json", {})
        citations = self._read_json(path / "citations.json", [])
        status = "ready" if manifest.exists() else "missing"
        return VectorIndex(
            namespace_id=namespace.namespace_id,
            path=str(path),
            manifest_path=str(manifest),
            chunk_store_path=str(path / "chunks.json"),
            embedding_store_path=str(path / "embeddings.json"),
            citation_store_path=str(path / "citations.json"),
            chunk_count=len(chunks) if isinstance(chunks, list) else 0,
            embedding_count=len(embeddings) if isinstance(embeddings, dict) else 0,
            citation_count=len(citations) if isinstance(citations, list) else 0,
            embedding_model=namespace.embedding_model,
            reranker_model=namespace.reranker_model,
            status=status,
        )

    def load_chunks(self, namespace: VectorNamespace) -> list[RAGChunk]:
        path = self.namespace_path(namespace) / "chunks.json"
        raw = self._read_json(path, [])
        chunks = []
        if isinstance(raw, list):
            for item in raw:
                try:
                    chunks.append(RAGChunk.model_validate(item))
                except Exception:
                    continue
        return chunks

    def save_chunks(self, namespace: VectorNamespace, chunks: list[RAGChunk], embeddings: dict[str, list[float]]) -> VectorIndex:
        path = self.namespace_path(namespace)
        if not self.policy.ensure_governed_path(path):
            raise ValueError("vectorstore_path_not_governed")
        path.mkdir(parents=True, exist_ok=True)
        current = self.load_chunks(namespace)
        merged = {chunk.chunk_id: chunk for chunk in [*current, *chunks]}
        merged_chunks = list(merged.values())
        citation_dump = [chunk.source.citation.model_dump() for chunk in merged_chunks]
        embedding_dump = self._read_json(path / "embeddings.json", {})
        if not isinstance(embedding_dump, dict):
            embedding_dump = {}
        embedding_dump.update(embeddings)
        (path / "chunks.json").write_text(json.dumps([chunk.model_dump() for chunk in merged_chunks], indent=2, ensure_ascii=False), encoding="utf-8")
        (path / "embeddings.json").write_text(json.dumps(embedding_dump, indent=2, ensure_ascii=False), encoding="utf-8")
        (path / "citations.json").write_text(json.dumps(citation_dump, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest = {
            "namespace_id": namespace.namespace_id,
            "embedding_model": namespace.embedding_model,
            "reranker_model": namespace.reranker_model,
            "chunk_count": len(merged_chunks),
            "embedding_count": len(embedding_dump),
            "citation_count": len(citation_dump),
        }
        (path / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return self.index(namespace)

    def _read_json(self, path: Path, default):
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return default

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "vector_index_store", "governed_paths_only": True}
