from __future__ import annotations

from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision
from aipinho.services.chat.chat_result_index_service import ChatResultIndexService


class FollowupResultRecallService:
    """Returns previous grounded chat results without asking the model to invent them."""

    def __init__(self, result_index: ChatResultIndexService | None = None) -> None:
        self.result_index = result_index or ChatResultIndexService()

    def recall(self, session_id: str, decision: ChatOperationDecision) -> ChatResponse:
        result_kind = str(decision.metadata.get("recall_kind") or "answer")
        result = self.result_index.latest_final_answer(session_id, result_kind=result_kind)
        if result is None:
            return ChatResponse(
                response_id=decision.operation_id,
                session_id=session_id,
                status="degraded",
                message=(
                    "Ainda nao tenho um resumo real e fundamentado nesta conversa para repetir. "
                    "Preciso de um resultado final indexado com evidencias antes de reapresentar conteudo anterior."
                ),
                intent={
                    "intent_type": "followup_result_recall",
                    "requires_task": False,
                    "requires_workspace": False,
                    "result_kind": result_kind,
                },
                policy={"approval_required_for": []},
                warnings=["grounded_result_not_found", "followup_recall_not_executed"],
                message_type="assistant_degraded_answer",
                operation_type=decision.operation_type,
                operation_id=decision.operation_id,
                is_final_answer=False,
                grounded=False,
                grounding_required=True,
                grounding_missing_reason="no_indexed_final_result",
            )
        result_ref_id = str(result.get("result_ref_id") or "")
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="ok",
            message=str(result.get("summary") or ""),
            intent={
                "intent_type": "followup_result_recall",
                "requires_task": False,
                "requires_workspace": False,
                "result_kind": result_kind,
            },
            policy={"approval_required_for": []},
            warnings=["followup_recall_grounded_in_result_index"],
            message_type="assistant_final_answer",
            operation_type=decision.operation_type,
            operation_id=decision.operation_id,
            result_ref_id=result_ref_id,
            evidence_refs=[{"type": "chat_result", "ref_id": result_ref_id}],
            is_final_answer=True,
            grounded=True,
        )
