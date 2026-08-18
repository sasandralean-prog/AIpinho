from __future__ import annotations

import hashlib

from aipinho.schemas.rag.integration.contracts import ContextProvenance


class ContextProvenanceService:
    def from_retrieval(self, *, source_id: str, source_type: str, retrieval_id: str, citation: dict, content: str, origin_reason: str) -> ContextProvenance:
        source_ref = citation.get("source_ref") or {}
        return ContextProvenance(
            source_type=source_type,
            source_id=source_id,
            retrieval_id=retrieval_id,
            citation_id=str(citation.get("citation_id") or ""),
            origin_reason=origin_reason,
            content_hash=str(source_ref.get("content_hash") or self._hash(content)),
            source_ref=source_ref,
        )

    def from_memory(self, *, memory: dict, citation_id: str, origin_reason: str) -> ContextProvenance:
        memory_id = str(memory.get("memory_id") or "")
        return ContextProvenance(
            source_type="curated_memory",
            source_id="curated_memory",
            memory_id=memory_id,
            memory_version=int(memory.get("version") or 0),
            citation_id=citation_id,
            origin_reason=origin_reason,
            content_hash=self._hash(str(memory.get("summary") or memory.get("text") or "")),
            source_ref={
                "source_id": "curated_memory",
                "source_type": "curated_memory",
                "ref": memory_id,
                "location": f"{memory_id}:v{memory.get('version')}",
            },
        )

    def validate(self, provenance: ContextProvenance) -> list[str]:
        reasons: list[str] = []
        if not provenance.source_id:
            reasons.append("provenance_source_id_missing")
        if not provenance.source_type:
            reasons.append("provenance_source_type_missing")
        if not provenance.citation_id:
            reasons.append("provenance_citation_id_missing")
        if provenance.source_type == "curated_memory" and (not provenance.memory_id or not provenance.memory_version):
            reasons.append("memory_provenance_incomplete")
        if provenance.source_type != "curated_memory" and not provenance.retrieval_id:
            reasons.append("retrieval_provenance_incomplete")
        return reasons

    def _hash(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "context_provenance", "required": True}
