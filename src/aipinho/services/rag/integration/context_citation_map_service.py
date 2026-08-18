from __future__ import annotations

from aipinho.schemas.rag.integration.contracts import ContextCitationMap, ContextInjectionItem
from aipinho.services.rag.integration.context_provenance_service import ContextProvenanceService


class ContextCitationMapService:
    def __init__(self, provenance: ContextProvenanceService | None = None) -> None:
        self.provenance = provenance or ContextProvenanceService()

    def build(self, items: list[ContextInjectionItem]) -> ContextCitationMap:
        item_map: dict[str, list[str]] = {}
        citations: dict[str, dict] = {}
        blocked: list[str] = []
        for item in items:
            if not item.citation_ids:
                blocked.append(f"{item.context_item_id}:citation_missing")
                continue
            provenance_reasons = self.provenance.validate(item.provenance)
            if provenance_reasons:
                blocked.extend(f"{item.context_item_id}:{reason}" for reason in provenance_reasons)
                continue
            item_map[item.context_item_id] = list(dict.fromkeys(item.citation_ids))
            for citation_id in item_map[item.context_item_id]:
                citations[citation_id] = {
                    "citation_id": citation_id,
                    "source_id": item.source_id,
                    "source_type": item.source_type,
                    "source_ref": item.provenance.source_ref,
                    "retrieval_id": item.provenance.retrieval_id,
                    "memory_id": item.provenance.memory_id,
                    "memory_version": item.provenance.memory_version,
                    "content_hash": item.provenance.content_hash,
                }
        valid = bool(items) and len(item_map) == len(items) and not blocked
        return ContextCitationMap(item_to_citations=item_map, citations=citations, valid=valid, blocked_reasons=list(dict.fromkeys(blocked)))

    def validate(self, citation_map: ContextCitationMap, items: list[ContextInjectionItem]) -> ContextCitationMap:
        expected = {item.context_item_id for item in items}
        mapped = set(citation_map.item_to_citations)
        reasons = list(citation_map.blocked_reasons)
        if expected != mapped:
            reasons.append("citation_map_incomplete")
        for citation_ids in citation_map.item_to_citations.values():
            for citation_id in citation_ids:
                if citation_id not in citation_map.citations:
                    reasons.append(f"citation_not_defined:{citation_id}")
        citation_map.valid = not reasons and bool(items)
        citation_map.blocked_reasons = list(dict.fromkeys(reasons))
        return citation_map

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "context_citation_map", "every_item_mapped": True}
