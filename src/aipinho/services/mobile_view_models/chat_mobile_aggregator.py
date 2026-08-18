from __future__ import annotations

from aipinho.schemas.mobile_view_models import MobileChatViewModel, MobileScreenState
from aipinho.schemas.interaction.contracts import ChatMessageRecord
from aipinho.services.interaction.interaction_core import ChatMessageService, ChatSessionService, ChatTimelineService
from aipinho.services.mobile_view_models.mobile_card_builder import MobileCardBuilder
from aipinho.services.mobile_view_models.mobile_evidence_mapper import MobileEvidenceMapper
from aipinho.services.mobile_view_models.mobile_presentation_mapper import MobilePresentationMapper
from aipinho.services.mobile_view_models.mobile_safe_action_builder import MobileSafeActionBuilder
from aipinho.services.mobile_view_models.mobile_sanitizer_service import MobileSanitizerService


class ChatMobileAggregator:
    def __init__(self) -> None:
        self.cards = MobileCardBuilder()
        self.evidence = MobileEvidenceMapper()
        self.actions = MobileSafeActionBuilder()
        self.sanitizer = MobileSanitizerService()
        self.presentation = MobilePresentationMapper()

    def view_model(self, session_id: str | None) -> MobileChatViewModel:
        resolved_session_id = self._resolve_session_id(session_id)
        label = resolved_session_id or "sem_sessao"
        messages = ChatMessageService().list(session_id=resolved_session_id, limit=80) if resolved_session_id else []
        event_count = len(ChatTimelineService().timeline(resolved_session_id).events) if resolved_session_id and ChatSessionService().get(resolved_session_id) else 0
        message_cards = [self._message_card(message) for message in messages]
        if resolved_session_id and not message_cards:
            message_cards.append(self._empty_session_card(resolved_session_id))
        cards = [
            self.cards.card(
                card_id="chat_speaker_truth",
                screen="chat",
                card_type="speaker_message",
                title="Chat/Speaker",
                status="completed" if resolved_session_id else "pending",
                severity="info",
                happening=f"Conversa carregada: {len(messages)} mensagem(ns) no historico.",
                why="O chat mostra mensagens humanas; detalhes tecnicos ficam no modo Detalhes/Raw.",
                safety="safe",
                safety_reason="Mensagem/copy sao sanitizados, raw fica oculto e chat simples nao executa tools.",
                actions=["Enviar mensagem.", "Copiar resposta.", "Recarregar historico."],
                evidence=[self.evidence.ref("event", f"chat:{label}", "chat session timeline")],
                metadata={"session_id": label, "raw_default_visible": False, "messages": len(messages), "events": event_count},
                safe_actions=[self.actions.refresh("chat")],
            ),
            *message_cards,
        ]
        cards.extend(self._context_cards(messages))
        cards.extend(self._artifact_cards(messages))
        return MobileChatViewModel(
            state=MobileScreenState(
                screen="chat",
                status=self._screen_status(messages, resolved_session_id),
                human_summary=f"Chat humano carregado para {label}: historico persistente, raw oculto, copy sanitizado e artifacts governados.",
            ),
            cards=cards,
            session_id=resolved_session_id,
            presentation=self.presentation.chat(session_id=resolved_session_id, messages=messages, cards=cards),
            trace_id="mobile_vm_chat",
        )

    def _resolve_session_id(self, session_id: str | None) -> str | None:
        sessions = ChatSessionService().list()
        if not sessions:
            return None
        if session_id and session_id != "latest" and ChatSessionService().get(session_id):
            return session_id
        latest = sorted(sessions, key=lambda item: item.updated_at)[-1]
        return latest.session_id

    def _message_card(self, message: ChatMessageRecord):
        role_title = {
            "user": "Voce",
            "assistant": "Assistente",
            "speaker": "Speaker",
            "system": "Sistema",
            "debugger": "Debugger",
        }.get(message.role, message.role)
        content = self.sanitizer.sanitize_text(message.content)
        status = str(message.metadata.get("chat_response_status", "completed")) if message.role == "assistant" else "completed"
        card_status = self._card_status(status)
        approval_required = str(message.metadata.get("approval_required", "False")).lower() == "true"
        rag_used = str(message.metadata.get("rag_used", "False")).lower() == "true"
        fallback_used = str(message.metadata.get("fallback_used", "False")).lower() == "true"
        safety = self._safety_answer(message, card_status, approval_required, rag_used, fallback_used)
        safety_reason = self._safety_reason(safety, card_status)
        card = self.cards.card(
            card_id=f"chat_message_{message.message_id}",
            screen="chat",
            card_type="chat_message",
            title=f"{role_title}",
            status=card_status,
            severity=self._severity(message, card_status, fallback_used),
            happening=content,
            why=self._why_for_message(message),
            safety=safety,
            safety_reason=safety_reason,
            actions=["Copiar mensagem sanitizada.", "Recarregar timeline.", "Abrir Debugger se a resposta estiver degradada."],
            evidence=[self.evidence.ref("event", message.message_id, f"mensagem {role_title.lower()}")],
            metadata={
                "session_id": message.session_id,
                "message_id": message.message_id,
                "role": message.role,
                "task_id": message.task_id or "null",
                "approval_required": approval_required,
                "rag_used": rag_used,
                "raw_available": False,
                "chunk": f"{message.chunk_index}/{message.chunk_total}",
                **{str(key): str(value) for key, value in message.metadata.items()},
            },
            event_ids=[message.source_event_id] if message.source_event_id else [],
        )
        card.copy_payload["summary"] = content
        card.copy_payload["raw_available"] = False
        card.copy_payload["copy_policy"] = "sanitized_only"
        return card

    def _card_status(self, status: str) -> str:
        normalized = status.strip().lower()
        if normalized in {"ok", "healthy"}:
            return "completed"
        if normalized == "preview":
            return "pending"
        if normalized in {"degraded", "offline", "blocked", "pending", "running", "completed", "failed", "unknown"}:
            return normalized
        return "completed"

    def _severity(self, message: ChatMessageRecord, card_status: str, fallback_used: bool) -> str:
        if message.role != "assistant":
            return "info"
        if card_status == "blocked":
            return "blocked"
        if card_status == "failed":
            return "danger"
        if card_status in {"degraded", "offline"} or fallback_used:
            return "warning"
        return "success"

    def _safety_answer(self, message: ChatMessageRecord, card_status: str, approval_required: bool, rag_used: bool, fallback_used: bool) -> str:
        message_type = str(message.metadata.get("message_type", "")).lower()
        if card_status == "blocked" or message_type == "blocked_policy_message":
            return "blocked"
        if card_status in {"failed", "offline"}:
            return "risky"
        if card_status == "degraded" or fallback_used or approval_required or rag_used:
            return "caution"
        return "safe"

    def _safety_reason(self, safety: str, card_status: str) -> str:
        if safety == "blocked":
            return "O backend registrou bloqueio/policy; detalhes ficam no painel tecnico."
        if safety == "risky":
            return "A resposta indica falha operacional ou indisponibilidade, sem expor raw no chat."
        if safety == "caution":
            return "Resposta degradada, com fallback, approval ou contexto externo marcado na metadata."
        return "Sem raw exposto, sem approval e sem task operacional vinculada."

    def _why_for_message(self, message: ChatMessageRecord) -> str:
        if message.role == "user":
            return "Mensagem registrada no historico persistente da conversa."
        if message.role == "assistant":
            message_type = str(message.metadata.get("message_type", "assistant_final_answer"))
            if message_type in {"task_preview", "artifact_offer", "artifact_preview"}:
                return "Isto e uma previa ou oferta operacional; ainda nao e uma conclusao final."
            if message_type == "assistant_degraded_answer":
                return "O backend nao encontrou evidencia suficiente para uma resposta final fundamentada."
            return "Resposta registrada pelo percurso conversacional do backend e salva na mesma sessao."
        return "Evento de conversa persistido para rastreabilidade sanitizada."

    def _screen_status(self, messages: list[ChatMessageRecord], session_id: str | None) -> str:
        if not session_id:
            return "pending"
        if messages:
            latest = messages[-1]
            if str(latest.metadata.get("requires_user_action", "False")).lower() == "true":
                return "pending"
        return "completed"

    def _empty_session_card(self, session_id: str):
        return self.cards.card(
            card_id=f"chat_empty_{session_id}",
            screen="chat",
            card_type="empty_chat",
            title="Conversa vazia",
            status="pending",
            severity="info",
            happening="Nenhuma mensagem persistida nesta sessao ainda.",
            why="O historico existe, mas a conversa ainda nao recebeu mensagem.",
            safety="safe",
            safety_reason="Sem raw, sem task e sem operacao pendente.",
            actions=["Enviar uma mensagem.", "Recarregar historico."],
            evidence=[self.evidence.ref("event", f"chat:{session_id}", "chat session timeline")],
            metadata={"session_id": session_id, "raw_available": False},
        )

    def _context_cards(self, messages: list[ChatMessageRecord]):
        context_refs = self._metadata_refs(messages, "context_bundle_id")
        rag_refs = self._metadata_refs(messages, "rag_citation_id")
        if not context_refs and not rag_refs:
            return []
        evidence = [
            *[self.evidence.ref("context_bundle", ref_id, "context bundle") for ref_id in context_refs],
            *[self.evidence.ref("rag_citation", ref_id, "RAG citation set") for ref_id in rag_refs],
        ]
        return [
            self.cards.card(
                card_id="chat_context_decision",
                screen="chat",
                card_type="context_decision",
                title="Contexto usado",
                status="completed",
                severity="info",
                happening="A resposta usou contexto rastreavel.",
                why="O backend retornou identificadores reais de contexto/citacao para auditoria.",
                safety="caution",
                safety_reason="Contexto externo ajuda a resposta, mas continua sendo evidência, não verdade automática.",
                actions=["Abrir evidencia.", "Copiar resumo.", "Abrir Debugger."],
                evidence=evidence,
                metadata={"context_policy": "sanitized_evidence_only"},
            )
        ]

    def _artifact_cards(self, messages: list[ChatMessageRecord]):
        artifact_refs = self._metadata_refs(messages, "artifact_id")
        if not artifact_refs:
            return []
        return [
            self.cards.card(
                card_id="chat_artifacts_feedback",
                screen="chat",
                card_type="artifact_feedback",
                title="Artifacts",
                status="healthy",
                severity="success",
                happening="Há artifacts reais associados a esta conversa.",
                why="Downloads/zip usam artifact_id governado pelo backend.",
                safety="safe",
                safety_reason="Artifact download nao usa path arbitrario no mobile.",
                actions=["Baixar artifact.", "Copiar artifact_id.", "Enviar feedback da mensagem."],
                evidence=[self.evidence.ref("artifact", artifact_id, "artifact registry") for artifact_id in artifact_refs],
                metadata={"artifact_policy": "artifact_id_only"},
            )
        ]

    def _metadata_refs(self, messages: list[ChatMessageRecord], key: str) -> list[str]:
        refs: list[str] = []
        for message in messages:
            value = str(message.metadata.get(key, "")).strip()
            if value and value.lower() not in {"latest", "null", "none", "unknown"} and value not in refs:
                refs.append(value)
        return refs
