from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class RolesAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("roles", ["/api/v1/roles", "/api/v1/role-models/status"], "healthy", "Roles explicam selecao, fallback e bloqueios.")

