from aipinho.schemas.rag.vector.contracts import RAGVectorHit, RerankRequest
from aipinho.services.rag.vector.rag_rerank_service import RAGRerankService

from vector_rag_test_helpers import citation, source_ref


def test_rag_rerank_service_is_read_only_and_keeps_citations():
    hit = RAGVectorHit(namespace_id="coder_rag", chunk_id="chunk_2", text="role namespace citation", score=0.1, source_ref=source_ref(), citation=citation())

    result = RAGRerankService().rerank(RerankRequest(query="role namespace", hits=[hit]))

    assert result.status == "ok"
    assert result.hits[0].source_ref.ref == "src/aipinho/example.py"
