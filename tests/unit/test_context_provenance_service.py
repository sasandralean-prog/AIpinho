from aipinho.services.rag.integration.context_provenance_service import ContextProvenanceService
from tests.unit.rag_memory_test_helpers import cited_retrieval, memory


def test_retrieval_provenance_requires_retrieval_id_and_hash():
    _, bundle = cited_retrieval()
    hit = bundle["hits"][0]
    provenance = ContextProvenanceService().from_retrieval(
        source_id=hit["source_id"],
        source_type=hit["source_type"],
        retrieval_id=bundle["retrieval_id"],
        citation=hit["citation"],
        content=hit["excerpt"],
        origin_reason="explicit_user_request",
    )
    assert provenance.retrieval_id == "retrieval_test"
    assert not ContextProvenanceService().validate(provenance)


def test_memory_provenance_requires_memory_id_and_version():
    provenance = ContextProvenanceService().from_memory(memory=memory(), citation_id="citation_memory_01", origin_reason="memory_explicit_read")
    assert provenance.memory_id == "memory_test"
    assert provenance.memory_version == 1
    assert not ContextProvenanceService().validate(provenance)


def test_missing_source_id_is_invalid():
    _, bundle = cited_retrieval()
    hit = bundle["hits"][0]
    provenance = ContextProvenanceService().from_retrieval(source_id="", source_type=hit["source_type"], retrieval_id=bundle["retrieval_id"], citation=hit["citation"], content=hit["excerpt"], origin_reason="explicit_user_request")
    assert "provenance_source_id_missing" in ContextProvenanceService().validate(provenance)

