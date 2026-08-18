from __future__ import annotations

from aipinho.schemas.rag.retrieval_request import Citation, RetrievalHit, RetrievalRequest, RetrievalScope, SourceRef


def request(**overrides):
    data = {
        "query": "validation gate",
        "sources": ["project_reports"],
        "scope": RetrievalScope(scope_type="project", source_ids=["project_reports"]),
        "explicit": True,
        "include_trace": True,
    }
    data.update(overrides)
    return RetrievalRequest(**data)


def cited_hit(excerpt: str = "Validation gate requires evidence.", score: float = 1.0) -> RetrievalHit:
    source_ref = SourceRef(source_id="project_reports", source_type="project_report", ref="reports/example.md", location="reports/example.md:10")
    citation = Citation(citation_type="report_section", source_ref=source_ref, excerpt=excerpt, line_start=10, line_end=10, section="Validation")
    return RetrievalHit(source_id="project_reports", source_type="project_report", title="Example", excerpt=excerpt, score=score, citation=citation, source_ref=source_ref)
