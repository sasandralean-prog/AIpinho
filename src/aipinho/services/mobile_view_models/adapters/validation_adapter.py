from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class ValidationAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("validation", ["/api/v1/validation/status", "/api/v1/validation/results/{validation_id}"], "unknown", "Validation cards explicam passed/failed e evidencias.")

