from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.schemas.chat.session_event import SessionEvent
from aipinho.schemas.chat.session_state import SessionState


def test_session_state_schema():
    state = SessionState(session_id="session_1", created_at="now", updated_at="now")
    assert state.recent_messages == []
    assert state.active_task_draft_id is None


def test_session_event_schema():
    event = SessionEvent(event_id="event_1", session_id="session_1", event_type="session_created", created_at="now", summary="created")
    assert event.data == {}


def test_chat_response_supports_session_and_task_draft():
    response = ChatResponse(response_id="chat_1", session_id="session_1", task_draft_id="draft_1", status="preview", message="ok")
    assert response.session_id == "session_1"
    assert response.task_draft_id == "draft_1"