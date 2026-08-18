from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class ApprovalAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("approval", ["/api/v1/approvals"], "unknown", "Approvals aparecem como preview e decisao humana, nunca aplicacao direta.")

