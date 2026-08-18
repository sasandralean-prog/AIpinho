from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class PatchAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("patch", ["/api/v1/patch-plans", "/api/v1/patch-plans/{plan_id}/diff"], "unknown", "Patch aparece como risco/qualidade/evidencia, sem apply direto.")

