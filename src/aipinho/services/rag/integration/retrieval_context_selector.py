from __future__ import annotations

from aipinho.schemas.rag.integration.contracts import ContextInjectionItem, RetrievalContextSelection
from aipinho.services.rag.integration.context_provenance_service import ContextProvenanceService


class RetrievalContextSelector:
    def __init__(self, provenance: ContextProvenanceService | None = None) -> None:
        self.provenance = provenance or ContextProvenanceService()

    def select(self, retrieval_result: dict | None, bundle: dict | None, *, usage_mode: str, max_items: int = 8) -> RetrievalContextSelection:
        result = retrieval_result or {}
        context = bundle or result.get("context_bundle") or {}
        status = str(result.get("status") or context.get("status") or "")
        warnings = list(result.get("warnings") or context.get("warnings") or [])
        blocked: list[str] = []
        blocked_items: list[dict] = []
        if status == "no_results":
            return RetrievalContextSelection(warnings=[*warnings, "retrieval_no_results"])
        if status not in {"found", "partial"}:
            blocked.append(f"retrieval_status_not_admissible:{status or 'missing'}")
        if not context.get("safe_for_prompt_assembly"):
            blocked.append("unsafe_retrieval_context_bundle")
        retrieval_id = str(result.get("retrieval_id") or context.get("retrieval_id") or "")
        items: list[ContextInjectionItem] = []
        for rank, hit in enumerate(context.get("hits") or result.get("hits") or [], start=1):
            citation = hit.get("citation") if isinstance(hit, dict) else None
            source_ref = citation.get("source_ref") if isinstance(citation, dict) else None
            if not citation or not citation.get("citation_id") or not source_ref or not source_ref.get("ref"):
                blocked_items.append({"source_id": hit.get("source_id") if isinstance(hit, dict) else None, "reason": "retrieval_hit_uncited"})
                continue
            content = str(hit.get("excerpt") or "")
            source_type = str(hit.get("source_type") or source_ref.get("source_type") or "")
            metadata = hit.get("metadata") or {}
            if source_type == "curated_memory":
                memory_id = str(metadata.get("memory_id") or source_ref.get("ref") or "")
                memory = {
                    "memory_id": memory_id,
                    "version": metadata.get("version") or metadata.get("memory_version") or 1,
                    "summary": content,
                }
                provenance = self.provenance.from_memory(
                    memory=memory,
                    citation_id=str(citation.get("citation_id") or ""),
                    origin_reason="memory_explicit_read",
                )
            else:
                provenance = self.provenance.from_retrieval(
                    source_id=str(hit.get("source_id") or source_ref.get("source_id") or ""),
                    source_type=source_type,
                    retrieval_id=retrieval_id,
                    citation=citation,
                    content=content,
                    origin_reason="explicit_user_request" if usage_mode == "explicit_user_request" else f"{usage_mode}_context",
                )
            items.append(
                ContextInjectionItem(
                    kind=self._kind(source_type),
                    source_type=provenance.source_type,
                    source_id=provenance.source_id,
                    content=content,
                    citation_ids=[provenance.citation_id],
                    provenance=provenance,
                    score=float(hit.get("score") or 0.0),
                    rank=rank,
                    warnings=list(hit.get("warnings") or []),
                    metadata={"retrieval_status": status, **metadata},
                )
            )
            if len(items) >= max_items:
                break
        if blocked_items:
            blocked.append("retrieval_contains_uncited_hits")
        return RetrievalContextSelection(items=items, blocked_items=blocked_items, warnings=list(dict.fromkeys(warnings)), blocked_reasons=list(dict.fromkeys(blocked)))

    def _kind(self, source_type: str) -> str:
        if source_type == "curated_memory":
            return "curated_memory"
        if source_type == "project_report":
            return "report_section"
        if source_type == "file":
            return "file_excerpt"
        if source_type in {"task_run_result", "validation_result", "patch_apply_result"}:
            return "evidence_item"
        return "retrieval_hit"

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "retrieval_context_selector", "executes_retrieval": False}
