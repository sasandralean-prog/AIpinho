from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class ContextAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("context", ["/api/v1/context/status", "/api/v1/context/debug/status"], "unknown", "Contexto aparece como evidencia admitida/rejeitada, nao como raw.")

