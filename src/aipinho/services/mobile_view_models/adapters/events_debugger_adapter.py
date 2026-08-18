from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class EventsDebuggerAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("events_debugger", ["/api/v1/events", "/api/v1/debugger/status"], "healthy", "Debugger e eventos ficam read-only, filtrados e copiaveis.")

