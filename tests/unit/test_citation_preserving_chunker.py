from aipinho.services.rag.vector.citation_preserving_chunker import CitationPreservingChunker

from vector_rag_test_helpers import ingestion_request


def test_citation_preserving_chunker_rejects_missing_source_or_citation():
    chunks, errors = CitationPreservingChunker().chunk(ingestion_request())
    assert chunks
    assert not errors
    assert chunks[0].source.citation is not None

    bad = ingestion_request()
    bad.citation = None
    chunks, errors = CitationPreservingChunker().chunk(bad)
    assert chunks == []
    assert "missing_source_ref_or_citation" in errors
