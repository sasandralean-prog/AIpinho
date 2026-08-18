from __future__ import annotations

from aipinho.schemas.rag.vector.contracts import RAGChunk
from aipinho.services.rag.vector.rag_sensitivity_gate import RAGSensitivityGate


class RAGChunkValidator:
    def __init__(self, sensitivity: RAGSensitivityGate | None = None) -> None:
        self.sensitivity = sensitivity or RAGSensitivityGate()

    def validate(self, chunk: RAGChunk) -> dict[str, object]:
        blocked: list[str] = []
        if not chunk.source.source_ref:
            blocked.append("missing_source_ref")
        if not chunk.source.citation:
            blocked.append("missing_citation")
        if not chunk.text.strip():
            blocked.append("empty_chunk")
        if len(chunk.text) > 5000:
            blocked.append("chunk_too_large")
        sensitivity = self.sensitivity.check(chunk.text, source_type=chunk.source.source_type)
        blocked.extend([str(item) for item in sensitivity.get("blocked_reasons", [])])
        return {"valid": not blocked, "status": "ok" if not blocked else "blocked", "blocked_reasons": list(dict.fromkeys(blocked))}

    def validate_many(self, chunks: list[RAGChunk]) -> dict[str, object]:
        blocked: list[str] = []
        for chunk in chunks:
            result = self.validate(chunk)
            blocked.extend([str(item) for item in result.get("blocked_reasons", [])])
        return {"valid": not blocked, "status": "ok" if not blocked else "blocked", "blocked_reasons": list(dict.fromkeys(blocked))}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "rag_chunk_validator", "source_ref_required": True, "citation_required": True}
