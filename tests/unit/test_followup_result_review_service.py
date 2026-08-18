from __future__ import annotations

from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision
from aipinho.services.chat.chat_result_index_service import ChatResultIndexService
from aipinho.services.chat.followup_result_review_service import FollowupResultReviewService


def _decision() -> ChatOperationDecision:
    return ChatOperationDecision(
        operation_id="chatop_review",
        operation_type="followup_result_review",
        message_type="assistant_final_answer",
        confidence=0.8,
        reasons=["test"],
        metadata={"recall_kind": "summary"},
    )


def test_followup_review_uses_indexed_summary_without_creating_task(tmp_path):
    index = ChatResultIndexService(root=tmp_path)
    session_id = "chat_test"
    index.add_final_answer(
        session_id,
        ChatResponse(
            response_id="response_test",
            session_id=session_id,
            status="ok",
            message="Plano macro: ler fontes, criar destino governado, validar e reportar.",
            intent={"intent_type": "readonly_analysis", "result_kind": "summary"},
            policy={"approval_required_for": []},
            message_type="assistant_final_answer",
            operation_type="readonly_analysis",
            is_final_answer=True,
            grounded=True,
        ),
        "msg_test",
    )

    response = FollowupResultReviewService(result_index=index).review(session_id, _decision())

    assert response.status == "ok"
    assert response.intent["requires_task"] is False
    assert response.intent["requires_workspace"] is False
    assert response.operation_type == "followup_result_review"
    assert "Plano macro" in response.message
    assert response.evidence_refs[0]["type"] == "chat_result"


def test_followup_review_without_indexed_result_is_degraded_not_patch(tmp_path):
    response = FollowupResultReviewService(result_index=ChatResultIndexService(root=tmp_path)).review("chat_empty", _decision())

    assert response.status == "degraded"
    assert response.intent["intent_type"] == "followup_result_review"
    assert response.intent["requires_task"] is False
    assert response.grounding_missing_reason == "no_indexed_final_result"
