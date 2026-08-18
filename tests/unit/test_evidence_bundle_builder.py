from aipinho.schemas.rag.retrieval_request import RetrievalHit
from aipinho.services.rag.evidence_bundle_builder import EvidenceBundleBuilder
from tests.unit.retrieval_test_helpers import cited_hit


def test_evidence_bundle_builder_accepts_cited_and_rejects_uncited_hits():
    builder = EvidenceBundleBuilder()
    assert builder.build([cited_hit()]).valid is True
    uncited = RetrievalHit(source_id="project_reports", source_type="project_report", excerpt="no citation")
    assert builder.build([uncited]).valid is False
