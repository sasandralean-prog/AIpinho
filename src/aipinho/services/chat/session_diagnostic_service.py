from __future__ import annotations

from aipinho.schemas.chat.chat_response import ChatResponse
from aipinho.services.chat.chat_operation_router_service import ChatOperationDecision
from aipinho.services.interaction.interaction_core import ChatMessageService


class SessionDiagnosticService:
    def diagnose(self, session_id: str, decision: ChatOperationDecision) -> ChatResponse:
        messages = ChatMessageService().list(session_id=session_id, limit=50)
        findings: list[str] = []
        for message in messages:
            metadata = message.metadata
            if metadata.get("message_type") in {"task_preview", "artifact_offer"} and metadata.get("is_final_answer") == "True":
                findings.append("preview_marked_as_final")
            if metadata.get("operation_type") in {"readonly_project_analysis", "artifact_request"} and not metadata.get("message_type"):
                findings.append("operation_without_message_type")
            if str(metadata.get("rag_citation_id", "")).lower() == "latest":
                findings.append("placeholder_evidence_latest")
            if message.role == "assistant" and metadata.get("message_type") == "assistant_final_answer" and metadata.get("grounded") == "False":
                findings.append("ungrounded_final_answer")
        unique = list(dict.fromkeys(findings))
        if unique:
            summary = "Diagnostico da conversa: encontrei sinais para revisar: " + ", ".join(unique) + "."
        else:
            summary = "Diagnostico da conversa: nao encontrei preview marcado como resposta final nem evidencia placeholder nesta sessao."
        return ChatResponse(
            response_id=decision.operation_id,
            session_id=session_id,
            status="ok",
            message=summary,
            intent={"intent_type": "session_diagnostic", "requires_task": False, "requires_workspace": False},
            policy={"approval_required_for": []},
            warnings=unique,
            message_type="system_diagnostic_result",
            operation_type=decision.operation_type,
            operation_id=decision.operation_id,
            is_final_answer=True,
            grounded=True,
            evidence_refs=[{"type": "chat_session", "ref_id": session_id}],
        )
