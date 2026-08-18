from aipinho.services.rag.sources.project_report_retrieval_source import ProjectReportRetrievalSource
from tests.unit.retrieval_test_helpers import request


def test_project_report_retrieval_source_returns_report_section_citations():
    hits = ProjectReportRetrievalSource().retrieve(request(query="validation gate"))
    assert hits
    assert all(hit.citation and hit.citation.citation_type == "report_section" for hit in hits)
