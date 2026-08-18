from __future__ import annotations

from aipinho.schemas.evals.contracts import EvalRequest
from aipinho.services.evals._shared import BaseEvaluator, finding


class CitationCoverageEvaluator(BaseEvaluator):
    evaluator = "citation_coverage"

    def evaluate(self, request: EvalRequest):
        payload = request.payload
        output_citations = set(payload.get("output_citation_ids", []) or [])
        available = set(payload.get("available_citation_ids", []) or [])
        contextual_claims = int(payload.get("contextual_claims", 0) or 0)
        findings = []
        if contextual_claims and not output_citations:
            findings.append(finding("missing_context_citations", "Contextual claims require citations"))
        fabricated = sorted(output_citations - available)
        if fabricated:
            findings.append(finding("fabricated_citation", "Output cites citation ids not present in context"))
        coverage = 1.0 if not contextual_claims else min(1.0, len(output_citations & available) / max(1, contextual_claims))
        return self.make_result(request, findings, {"coverage": coverage, "fabricated": fabricated})
