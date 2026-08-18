from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class MonitorAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("monitor", ["/api/v1/monitor/status", "/api/v1/monitor/services", "/api/v1/monitor/resources"], "degraded", "Monitor e recursos aparecem como observabilidade, sem decisao local de policy.")

