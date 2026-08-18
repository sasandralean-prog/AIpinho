from __future__ import annotations

from aipinho.schemas.rag.retrieval_request import RetrievalHit, RetrievalRequest, RetrievalTrace
from aipinho.services.rag.retrieval_router_service import RetrievalRouterService
from aipinho.services.rag.retrieval_source_registry import RetrievalSourceRegistry
from aipinho.services.rag.retrieval_trace_service import RetrievalTraceService


class RetrievalExecutor:
    def __init__(self, registry: RetrievalSourceRegistry | None = None, router: RetrievalRouterService | None = None, trace_service: RetrievalTraceService | None = None) -> None:
        self.registry = registry or RetrievalSourceRegistry()
        self.router = router or RetrievalRouterService()
        self.trace_service = trace_service or RetrievalTraceService()

    def execute(self, request: RetrievalRequest, source_ids: list[str]) -> tuple[list[RetrievalHit], list[RetrievalTrace], list[str]]:
        hits: list[RetrievalHit] = []
        trace: list[RetrievalTrace] = []
        warnings: list[str] = []
        for source_id in source_ids:
            source = self.registry.get_source(source_id)
            if source is None:
                trace.append(self.trace_service.item("source_execute", "blocked", "unregistered_source", source_id=source_id))
                warnings.append(f"unregistered_source:{source_id}")
                continue
            adapter = self.router.adapter_for(source.adapter)
            if adapter is None:
                trace.append(self.trace_service.item("source_execute", "degraded", "adapter_missing", source_id=source_id, data={"adapter": source.adapter}))
                warnings.append(f"adapter_missing:{source.adapter}")
                continue
            try:
                source_hits = adapter.retrieve(request)
                hits.extend(source_hits)
                trace.append(self.trace_service.item("source_execute", "ok", "source_retrieved", source_id=source_id, data={"hits": len(source_hits)}))
            except Exception as exc:
                trace.append(self.trace_service.item("source_execute", "degraded", "adapter_failed", source_id=source_id, data={"error": str(exc)[:500]}))
                warnings.append(f"adapter_failed:{source_id}")
        return hits, trace, list(dict.fromkeys(warnings))

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "retrieval_executor", "side_effects": False}
