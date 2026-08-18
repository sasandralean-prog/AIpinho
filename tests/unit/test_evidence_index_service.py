from aipinho.schemas.reports.evidence_citation import EvidenceCitation
from aipinho.services.reports.evidence_index_service import EvidenceIndexService


def test_evidence_index_queries_by_path_pattern_source_and_summary():
    evidence = [
        EvidenceCitation(evidence_id="e1", source_type="file", path="src/a.py", confidence=0.8),
        EvidenceCitation(evidence_id="e2", source_type="policy", path="config/policies/x.yaml", confidence=0.8),
    ]
    index = EvidenceIndexService(evidence)

    assert index.find_by_path("src/a.py")[0].evidence_id == "e1"
    assert index.find_by_pattern("config/**/*.yaml")[0].evidence_id == "e2"
    assert index.find_by_source_type("policy")[0].path == "config/policies/x.yaml"
    summary = index.summarize()
    assert summary["vectorstore_enabled"] is False
    assert summary["embedding_enabled"] is False
