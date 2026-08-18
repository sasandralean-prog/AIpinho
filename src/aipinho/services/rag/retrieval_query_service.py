from __future__ import annotations

import re

from aipinho.schemas.rag.retrieval_request import RetrievalBudget, RetrievalQuery, RetrievalValidation


class RetrievalQueryService:
    def normalize(self, query: str, budget: RetrievalBudget | None = None) -> RetrievalQuery:
        budget = budget or RetrievalBudget()
        text = (query or "").strip()
        if len(text) > budget.max_query_chars:
            text = text[: budget.max_query_chars]
        normalized = " ".join(text.lower().split())
        tokens = [token for token in re.findall(r"[a-z0-9_]+", normalized) if len(token) > 1]
        return RetrievalQuery(text=text, normalized=normalized, tokens=list(dict.fromkeys(tokens)))

    def validate(self, query: RetrievalQuery) -> RetrievalValidation:
        if not query.normalized:
            return RetrievalValidation(valid=False, status="blocked", blocked_reasons=["empty_query"])
        return RetrievalValidation(valid=True, status="ok")

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "retrieval_query", "deterministic": True}
