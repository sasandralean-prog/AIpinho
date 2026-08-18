from __future__ import annotations

from aipinho.schemas.chat.chat_response import ChatNextAction, ChatResponse
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision


class ReadonlyProjectAnalysisPreviewService:
    def from_response(self, response: ChatResponse, decision: ChatOperationDecision) -> ChatResponse:
        preview_id = response.preview_id or response.task_preview_id
        target = decision.workspace or "workspace informado"
        needs_clarification = response.status == "needs_clarification"
        message = (
            (
                f"Antes de iniciar a analise somente leitura de {target}, preciso confirmar o escopo indicado no preview. "
                "Ainda nao li arquivos nem gerei conclusao sobre o projeto."
            )
            if needs_clarification
            else (
                f"Posso iniciar uma analise somente leitura de {target}. "
                "Ainda nao li arquivos nem gerei conclusao sobre o projeto; isto e uma previa operacional. "
                "Para produzir um resumo real, use a acao de task/read-only e acompanhe a validacao no Debugger."
            )
        )
        next_actions = list(response.next_actions)
        if not needs_clarification and preview_id and not any(action.target_id == preview_id for action in next_actions):
            next_actions.insert(0, ChatNextAction(type="create_task_run", label="Iniciar task read-only", target_id=preview_id))
        return response.model_copy(update={
            "status": response.status if needs_clarification else "preview",
            "message": message,
            "intent": {"intent_type": "readonly_project_analysis", "requires_task": True, "requires_workspace": True},
            "policy": {"approval_required_for": [], "read_only": True},
            "message_type": "task_preview",
            "operation_type": decision.operation_type,
            "operation_id": decision.operation_id,
            "task_preview_id": preview_id,
            "requires_user_action": True,
            "is_final_answer": False,
            "grounded": False,
            "grounding_required": True,
            "grounding_missing_reason": "read_files_not_executed",
            "next_actions": next_actions,
            "warnings": list(dict.fromkeys([*response.warnings, "readonly_preview_not_project_summary"])),
        })
