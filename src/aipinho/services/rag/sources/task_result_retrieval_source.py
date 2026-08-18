from __future__ import annotations

from aipinho.schemas.rag.retrieval_request import RetrievalHit, RetrievalRequest
from aipinho.services.rag.citation_builder import CitationBuilder
from aipinho.services.runtime.task_run_store import TaskRunStore


class TaskResultRetrievalSource:
    source_id = "task_results"

    def __init__(self, store: TaskRunStore | None = None, citations: CitationBuilder | None = None) -> None:
        self.store = store or TaskRunStore()
        self.citations = citations or CitationBuilder()

    def retrieve(self, request: RetrievalRequest) -> list[RetrievalHit]:
        if not request.run_id:
            return []
        result = self.store.get_result(request.run_id)
        if result is None or not result.safe_to_display:
            return []
        excerpt = result.summary[: request.budget.max_hit_excerpt_chars]
        citation = self.citations.build(
            citation_type="task_result_field",
            source_id=self.source_id,
            source_type="task_run_result",
            ref=result.run_id,
            location=f"{result.run_id}:summary",
            section="summary",
            excerpt=excerpt,
        )
        return [
            RetrievalHit(
                source_id=self.source_id,
                source_type="task_run_result",
                title=f"Task result {result.run_id}",
                excerpt=excerpt,
                citation=citation,
                source_ref=citation.source_ref,
                metadata={
                    "run_id": result.run_id,
                    "status": result.status,
                    "safe_to_display": result.safe_to_display,
                    "events_count": result.events_count,
                },
            )
        ]

    def status(self) -> dict[str, object]:
        return {"status": "ok", "source": self.source_id, "read_only": True, "required_lookup": "run_id"}
