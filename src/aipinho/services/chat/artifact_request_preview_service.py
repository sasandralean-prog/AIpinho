from __future__ import annotations

from aipinho.schemas.chat.chat_response import ChatNextAction, ChatResponse
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision


class ArtifactRequestPreviewService:
    def offer(self, decision: ChatOperationDecision, factual_response: ChatResponse | None = None) -> ChatResponse:
        factual_text = factual_response.message.strip() if factual_response and factual_response.status == "ok" else ""
        prefix = f"Resposta: {factual_text}\n\n" if factual_text else ""
        message = (
            f"{prefix}Posso preparar um artifact governado, mas preciso de conteudo final ou fonte operacional validada antes de criar download. "
            "Nenhum arquivo foi criado ainda e nao ha link de download ate existir um artifact_id real."
        )
        base = factual_response.model_dump() if factual_response is not None else {}
        return ChatResponse(
            response_id=str(base.get("response_id") or decision.operation_id),
            session_id=base.get("session_id"),
            status="preview",
            message=message,
            intent={"intent_type": "artifact_request", "requires_task": False, "requires_workspace": False},
            policy={"approval_required_for": ["artifact_preview"]},
            next_actions=[
                ChatNextAction(type="preview_artifact", label="Preparar preview de artefato", target_id=decision.operation_id),
                ChatNextAction(type="cancel", label="Manter apenas a resposta no chat", target_id=decision.operation_id),
            ],
            warnings=["artifact_not_created_without_preview", "download_link_requires_artifact_id"],
            model_used=base.get("model_used"),
            real_inference=base.get("real_inference"),
            fallback_used=bool(base.get("fallback_used", False)),
            trace=base.get("trace", []),
            message_type="artifact_offer",
            operation_type=decision.operation_type,
            operation_id=decision.operation_id,
            requires_user_action=True,
            is_final_answer=False,
            grounded=bool(factual_text),
            grounding_required=True,
            grounding_missing_reason=None if factual_text else "factual_response_not_available",
        )
