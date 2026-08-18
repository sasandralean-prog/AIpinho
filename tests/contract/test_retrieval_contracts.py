from aipinho.schemas.rag.retrieval_request import Citation, EvidenceBundle, RetrievalContextBundle, RetrievalHit, RetrievalRequest, RetrievalResult, RetrievalScope, RetrievalQuery, SourceRef


def test_retrieval_contracts_validate_cited_context():
    source_ref = SourceRef(source_id="project_reports", source_type="project_report", ref="report.md", location="report.md:1")
    citation = Citation(citation_type="report_section", source_ref=source_ref, excerpt="Evidence")
    hit = RetrievalHit(source_id="project_reports", source_type="project_report", excerpt="Evidence", citation=citation, source_ref=source_ref)
    request = RetrievalRequest(query="evidence", sources=["project_reports"], scope=RetrievalScope(scope_type="project"), explicit=True)
    bundle = RetrievalContextBundle(status="found", query=request.query, hits=[hit], citations=[citation], source_refs=[source_ref], evidence_bundle=EvidenceBundle(citations=[citation], evidence_count=1), safe_for_prompt_assembly=True)
    result = RetrievalResult(status="found", query=RetrievalQuery(text="evidence", normalized="evidence", tokens=["evidence"]), sources_requested=request.sources, hits=[hit], context_bundle=bundle)
    assert result.context_bundle.safe_for_prompt_assembly is True
