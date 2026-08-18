from aipinho.schemas.rag.retrieval_request import Citation, SourceRef
from aipinho.services.rag.source_ref_validator import SourceRefValidator


def test_source_ref_validator_requires_source_id_ref_and_excerpt():
    validator = SourceRefValidator()
    valid = Citation(citation_type="evidence_id", source_ref=SourceRef(source_id="source", source_type="report", ref="report:1"), excerpt="evidence")
    assert validator.validate_citation(valid)["valid"] is True
    assert validator.validate_citation(None)["valid"] is False
