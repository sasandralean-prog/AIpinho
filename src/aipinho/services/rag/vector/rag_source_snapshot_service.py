from __future__ import annotations

import hashlib

from aipinho.schemas.rag.vector.contracts import RAGIngestionRequest


class RAGSourceSnapshotService:
    def snapshot(self, request: RAGIngestionRequest) -> dict[str, object]:
        content_hash = hashlib.sha256(request.text.encode("utf-8")).hexdigest() if request.text else None
        return {
            "status": "ok" if content_hash else "blocked",
            "source_type": request.source_type,
            "source_id": request.source_id,
            "source_hash": content_hash,
            "source_ref": request.source_ref.model_dump() if request.source_ref else None,
            "citation": request.citation.model_dump() if request.citation else None,
        }

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "rag_source_snapshot", "workspace_source_mutation_enabled": False}
