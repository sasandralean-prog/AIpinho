from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class ReplayRegressionAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("replay_regression", ["/api/v1/replay/status", "/api/v1/regression/status"], "unknown", "Replay/regression aparecem como diagnostico, sem corrigir sozinho.")

