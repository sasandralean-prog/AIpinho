from aipinho.schemas.rag.retrieval_request import RetrievalHit
from aipinho.services.rag.retrieval_context_builder import RetrievalContextBuilder
from tests.unit.retrieval_test_helpers import cited_hit, request


def test_retrieval_context_builder_builds_safe_cited_bundle():
    bundle = RetrievalContextBuilder().build(request(), [cited_hit()])
    assert bundle.safe_for_prompt_assembly is True
    assert bundle.citations
    assert bundle.source_refs


def test_retrieval_context_builder_blocks_uncited_context():
    bundle = RetrievalContextBuilder().build(request(), [RetrievalHit(source_id="project_reports", source_type="project_report", excerpt="uncited")])
    assert bundle.safe_for_prompt_assembly is False
    assert "citation_missing" in bundle.blocked_reasons
