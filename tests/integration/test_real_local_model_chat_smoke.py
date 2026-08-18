from __future__ import annotations

import os

import pytest

from aipinho.schemas.chat.chat_request import ChatContext, ChatRequest
from aipinho.services.chat.chat_service import ChatService

pytestmark = [pytest.mark.real_inference, pytest.mark.manual]


def test_real_local_model_simple_chat_smoke() -> None:
    if os.environ.get("AIPINHO_RUN_REAL_INFERENCE_TESTS") != "1":
        pytest.skip("Set AIPINHO_RUN_REAL_INFERENCE_TESTS=1 to run local real-model smoke.")

    response = ChatService().respond(
        ChatRequest(
            message="Quanto e 2+2?",
            mode="normal",
            include_trace=True,
            context=ChatContext(surface="api"),
        )
    )

    assert response.status in {"ok", "degraded"}
    assert response.task_draft_id is None
    assert response.citation_map == {}
    assert response.policy.get("approval_required_for", []) == []
    assert response.model_used not in {None, "stub.default"}
    assert response.real_inference is True
    assert response.fallback_used is False
    trace = [item.model_dump() for item in response.trace]
    assert any(item["stage"] in {"conversation_model_selection", "model_selected"} for item in trace)
    assert any(item["stage"] in {"conversation_model_response", "model_run_completed"} for item in trace)
