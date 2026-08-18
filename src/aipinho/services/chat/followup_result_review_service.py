from __future__ import annotations

from typing import Any

from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision
from aipinho.services.chat.chat_result_index_service import ChatResultIndexService


class FollowupResultReviewService:
    """Builds grounded reviews from the previous indexed chat result."""

    def __init__(self, result_index: ChatResultIndexService | None = None) -> None:
        self.result_index = result_index or ChatResultIndexService()

    def review(self, session_id: str, decision: ChatOperationDecision) -> ChatResponse:
        result = self.result_index.latest_final_answer(session_id, result_kind="summary")
        if result is None:
            result = self.result_index.latest_final_answer(session_id, result_kind="answer")
        if result is None:
            return ChatResponse(
                response_id=decision.operation_id,
                session_id=session_id,
                status="degraded",
                message=(
                    "Ainda nao tenho um resultado fundamentado nesta conversa para revisar. "
                    "Execute ou conclua uma etapa primeiro; depois eu consigo revisar o plano, riscos e proximos passos."
                ),
                intent={"intent_type": "followup_result_review", "requires_task": False, "requires_workspace": False},
                policy={"approval_required_for": []},
                warnings=["grounded_result_not_found", "followup_review_not_executed"],
                message_type="assistant_degraded_answer",
                operation_type=decision.operation_type,
                operation_id=decision.operation_id,
                is_final_answer=False,
                grounded=False,
                grounding_required=True,
                grounding_missing_reason="no_indexed_final_result",
            )

        summary = str(result.get("summary") or "").strip()
        result_ref_id = str(result.get("result_ref_id") or "")
        excerpt = self._excerpt(summary)
        message = (
            "Revisei o ultimo resultado fundamentado desta conversa.\n\n"
            "Veredito: o plano pode avancar somente se a proxima etapa continuar pelo fluxo governado "
            "correto: contrato explicito, policy/capability, preview quando houver escrita, approval quando "
            "exigido e validacao antes de declarar sucesso.\n\n"
            "Pontos de atencao:\n"
            "- confirme que objetivo, fonte, destino e entregaveis estao claros no resultado anterior;\n"
            "- mantenha leitura, escrita, shell e artifacts separados pelas policies correspondentes;\n"
            "- se a execucao criar ou alterar arquivos, nao trate isso como read-only;\n"
            "- se faltar evidencia, peca novo diagnostico em vez de inventar conclusao.\n\n"
            "Evidencia revisada:\n"
            f"{excerpt}"
        )
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="ok",
            message=message,
            intent={
                "intent_type": "followup_result_review",
                "requires_task": False,
                "requires_workspace": False,
                "result_kind": "summary",
            },
            policy={"approval_required_for": []},
            warnings=["followup_review_grounded_in_latest_result", "review_does_not_execute"],
            message_type="assistant_final_answer",
            operation_type=decision.operation_type,
            operation_id=decision.operation_id,
            result_ref_id=result_ref_id,
            evidence_refs=[{"type": "chat_result", "ref_id": result_ref_id}],
            is_final_answer=True,
            grounded=True,
        )

    def _excerpt(self, text: str, *, max_chars: int = 1200) -> str:
        compact = "\n".join(line.rstrip() for line in text.splitlines() if line.strip())
        if not compact:
            return "Resultado anterior registrado sem texto resumido disponivel."
        if len(compact) <= max_chars:
            return compact
        return compact[: max_chars - 40].rstrip() + "\n...[trecho compactado para revisao]"
