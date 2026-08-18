import pytest
from pydantic import ValidationError

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.chat.chat_response import ChatResponse


def test_chat_request_defaults():
    request = ChatRequest(message="ola")
    assert request.mode == "normal"
    assert request.include_trace is False
    assert request.context is None


def test_chat_request_requires_message():
    with pytest.raises(ValidationError):
        ChatRequest()


def test_chat_request_rejects_unknown_mode():
    with pytest.raises(ValidationError):
        ChatRequest(message="ola", mode="execute")


def test_chat_response_trace_optional():
    response = ChatResponse(response_id="chat_1", status="ok", message="ok")
    assert response.trace == []
    assert response.raw_debug_ref is None


def test_chat_response_rejects_unknown_status():
    with pytest.raises(ValidationError):
        ChatResponse(response_id="chat_1", status="running", message="bad")