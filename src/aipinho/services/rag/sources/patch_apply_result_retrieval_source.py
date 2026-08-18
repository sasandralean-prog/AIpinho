from __future__ import annotations

from aipinho.schemas.rag.retrieval_request import RetrievalHit, RetrievalRequest
from aipinho.services.patching.apply.patch_apply_store import PatchApplyStore
from aipinho.services.rag.citation_builder import CitationBuilder


class PatchApplyResultRetrievalSource:
    source_id = "patch_apply_results"

    def __init__(self, store: PatchApplyStore | None = None, citations: CitationBuilder | None = None) -> None:
        self.store = store or PatchApplyStore()
        self.citations = citations or CitationBuilder()

    def retrieve(self, request: RetrievalRequest) -> list[RetrievalHit]:
        if not request.apply_run_id:
            return []
        result = self.store.get_result(request.apply_run_id)
        if result is None:
            return []
        changed_count = sum(1 for item in result.files if item.changed)
        excerpt = (
            f"Patch apply {result.status}; safe_to_report_success={result.safe_to_report_success}; "
            f"changed_files={changed_count}; validation={result.post_apply_validation.status}; "
            f"rollback={result.rollback.status}."
        )[: request.budget.max_hit_excerpt_chars]
        citation = self.citations.build(
            citation_type="patch_apply_field",
            source_id=self.source_id,
            source_type="patch_apply_result",
            ref=result.apply_run_id,
            location=f"{result.apply_run_id}:result",
            section="apply_result",
            excerpt=excerpt,
        )
        return [
            RetrievalHit(
                source_id=self.source_id,
                source_type="patch_apply_result",
                title=f"Patch apply {result.apply_run_id}",
                excerpt=excerpt,
                citation=citation,
                source_ref=citation.source_ref,
                metadata={
                    "apply_run_id": result.apply_run_id,
                    "plan_id": result.plan_id,
                    "status": result.status,
                    "safe_to_report_success": result.safe_to_report_success,
                    "changed_files": changed_count,
                    "post_apply_validation": result.post_apply_validation.status,
                },
            )
        ]

    def status(self) -> dict[str, object]:
        return {"status": "ok", "source": self.source_id, "read_only": True, "required_lookup": "apply_run_id"}
