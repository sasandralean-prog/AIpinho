from aipinho.schemas.chat.chat_message import ChatMessage
from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.chat.session_state import SessionState
from aipinho.services.session.session_context_service import SessionContextService


def test_session_context_short_summary_and_active_draft():
    state = SessionState(
        session_id="session_test",
        created_at="2026-01-01T00:00:00+00:00",
        updated_at="2026-01-01T00:00:00+00:00",
        recent_messages=[ChatMessage(role="user", content="uma"), ChatMessage(role="user", content="duas")],
        last_intent_map={"intent_type": "readonly_analysis"},
        active_workspace_candidate="C:\\Dev\\AIpinho",
        active_task_draft_id="draft_1",
    )
    context = SessionContextService().build(ChatRequest(message="continue"), state)
    assert context.last_intent_type == "readonly_analysis"
    assert context.last_workspace_candidate == "C:\\Dev\\AIpinho"
    assert context.active_task_draft_id == "draft_1"
    assert "uma" in context.recent_summary


def test_session_context_without_state_does_not_invent():
    context = SessionContextService().build(ChatRequest(message="ola"), None)
    assert context.current_message == "ola"
    assert context.last_workspace_candidate is None