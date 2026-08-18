from aipinho.schemas.chat.chat_response import ChatNextAction, ChatResponse
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision
from aipinho.services.chat.readonly_project_analysis_preview_service import ReadonlyProjectAnalysisPreviewService


def _decision() -> ChatOperationDecision:
    return ChatOperationDecision(
        operation_id="chatop_test",
        operation_type="readonly_project_analysis",
        message_type="task_preview",
        confidence=0.9,
        workspace="C:\\Workspace",
    )


def test_readonly_adapter_does_not_offer_execution_while_clarification_is_required():
    response = ChatResponse(
        response_id="chat_test",
        status="needs_clarification",
        message="Preciso esclarecer.",
        preview_id="preview_test",
        task_preview_id="preview_test",
        next_actions=[ChatNextAction(type="clarify", label="Responder esclarecimento", target_id="draft_test")],
    )

    adapted = ReadonlyProjectAnalysisPreviewService().from_response(response, _decision())

    assert adapted.status == "needs_clarification"
    assert [action.type for action in adapted.next_actions] == ["clarify"]


def test_readonly_adapter_offers_execution_for_ready_preview():
    response = ChatResponse(
        response_id="chat_test",
        status="preview",
        message="Preview pronto.",
        preview_id="preview_test",
        task_preview_id="preview_test",
    )

    adapted = ReadonlyProjectAnalysisPreviewService().from_response(response, _decision())

    assert adapted.status == "preview"
    assert adapted.next_actions[0].type == "create_task_run"
