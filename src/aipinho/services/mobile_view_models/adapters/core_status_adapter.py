from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class CoreStatusAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("core", ["/api/v1/health", "/api/v1/status", "/api/v1/config/status"], "healthy", "Core API responde por status e contrato /api/v1.")

