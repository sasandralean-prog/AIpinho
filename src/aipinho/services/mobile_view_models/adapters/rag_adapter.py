from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class RagAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("rag", ["/api/v1/rag/status", "/api/v1/vector-rag/namespaces", "/api/v1/legacy-rag/status"], "degraded", "RAG legado aparece com warning e nao como verdade atual.")

