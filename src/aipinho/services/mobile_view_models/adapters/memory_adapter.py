from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class MemoryAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("memory", ["/api/v1/memory/status", "/api/v1/memory/curated"], "healthy", "Memory mostra candidates/curated/superseded sem ingerir raw.")

