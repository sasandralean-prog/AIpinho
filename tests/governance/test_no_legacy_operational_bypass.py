import inspect

from aipinho.app_factory import create_app
from aipinho.services.governance.lifecycle.canonical_public_chat_service import CanonicalPublicChatService


CRITICAL_ROUTES = [
    ("/api/v1/chat", "POST"),
    ("/api/v1/chat/sessions/{session_id}/send", "POST"),
    ("/v1/chat/completions", "POST"),
    ("/v1/integrations/continue/chat", "POST"),
]


def _first_endpoint_module(path: str, method: str) -> str:
    app = create_app()
    for route in app.routes:
        if getattr(route, "path", None) != path:
            continue
        methods = getattr(route, "methods", set()) or set()
        if method in methods:
            return route.endpoint.__module__
    raise AssertionError(f"route not found: {method} {path}")


def test_no_legacy_operational_bypass_for_public_critical_routes() -> None:
    for path, method in CRITICAL_ROUTES:
        assert _first_endpoint_module(path, method).endswith("governance_lifecycle_router")


def test_canonical_public_chat_evaluates_lifecycle_before_legacy_chat() -> None:
    source = inspect.getsource(CanonicalPublicChatService.respond)
    assert source.index("self.lifecycle.evaluate") < source.index("self._conversation_response")
    assert "self.chat_service.respond" not in source
