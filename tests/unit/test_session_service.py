from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.services.session.session_service import SessionService
from aipinho.services.session.session_store import SessionStore


class DummyWorkspace:
    declared = False
    protected = False
    path = None


class DummyIntent:
    intent_id = "intent_test"
    intent_type = "conversation"
    task_type = "none"
    requires_task = False
    requires_workspace = False
    warnings = []
    workspace = DummyWorkspace()


class DummyPolicy:
    status = "allowed"
    contract_type = "conversation"
    allowed_actions = []
    denied_actions = []
    approval_required_for = []
    safe_to_execute = False
    safe_to_preview = False


def test_session_create_get_delete(tmp_path):
    service = SessionService(store=SessionStore(tmp_path))
    state = service.create_session(surface="api")
    assert state.session_id
    assert service.get_session(state.session_id).session_id == state.session_id
    assert service.delete_session(state.session_id) is True
    assert service.get_session(state.session_id) is None


def test_session_append_sanitized_event_and_message(tmp_path):
    service = SessionService(store=SessionStore(tmp_path))
    state = service.create_session(surface="api")
    updated = service.update_after_chat(state, ChatRequest(message="token=abc123"), DummyIntent(), DummyPolicy())
    assert "token=abc123" not in updated.recent_messages[-1].content
    assert "[redacted]" in updated.recent_messages[-1].content
    events = service.list_events(updated.session_id)
    assert events


def test_session_limits_recent_messages(tmp_path):
    service = SessionService(store=SessionStore(tmp_path))
    state = service.create_session(surface="api")
    for index in range(service.policy.max_recent_messages() + 3):
        state = service.update_after_chat(state, ChatRequest(message=f"msg {index}"), DummyIntent(), DummyPolicy())
    assert len(state.recent_messages) == service.policy.max_recent_messages()


def test_requested_chat_session_id_is_preserved_for_operational_state(tmp_path):
    service = SessionService(store=SessionStore(tmp_path))

    state = service.ensure_session(ChatRequest(message="Analise em modo read-only.", session_id="chat_persistent_123"))

    assert state.session_id == "chat_persistent_123"
    assert service.get_session("chat_persistent_123") is not None
