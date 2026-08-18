from __future__ import annotations

from aipinho.schemas.rag.retrieval_request import RetrievalBudget, RetrievalHit


class RetrievalBudgetService:
    def apply(self, hits: list[RetrievalHit], budget: RetrievalBudget) -> tuple[list[RetrievalHit], list[str], str]:
        warnings: list[str] = []
        limited = hits[: budget.max_hits_total]
        if len(hits) > len(limited):
            warnings.append("hit_budget_truncated")
        chars = 0
        output: list[RetrievalHit] = []
        for hit in limited:
            if len(hit.excerpt) > budget.max_hit_excerpt_chars:
                hit.excerpt = hit.excerpt[: budget.max_hit_excerpt_chars]
                hit.warnings.append("excerpt_truncated")
                warnings.append("excerpt_truncated")
            chars += len(hit.excerpt)
            if chars > budget.max_context_chars:
                warnings.append("context_budget_truncated")
                break
            output.append(hit)
        status = "partial" if warnings and output else "found" if output else "no_results"
        return output, list(dict.fromkeys(warnings)), status

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "retrieval_budget"}
