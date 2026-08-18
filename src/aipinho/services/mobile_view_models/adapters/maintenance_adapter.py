from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class MaintenanceAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("maintenance", ["/api/v1/maintenance/status", "/api/v1/maintenance/invariants"], "unknown", "Maintenance mostra invariants, proposals e planos em preview.")

