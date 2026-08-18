from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class ModelsAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("models", ["/api/v1/models/status", "/api/v1/models"], "healthy", "Modelos mostram auto/manual/fallback sem inferencia real no mobile.")

