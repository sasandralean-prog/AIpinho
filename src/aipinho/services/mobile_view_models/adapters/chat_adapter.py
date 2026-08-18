from aipinho.services.mobile_view_models.adapters.base import DomainStatusAdapter


class ChatAdapter(DomainStatusAdapter):
    def __init__(self) -> None:
        super().__init__("chat", ["/api/v1/chat/status", "/api/v1/chat/sessions"], "healthy", "Chat usa sessoes, timeline, copy sanitizado e feedback.")

