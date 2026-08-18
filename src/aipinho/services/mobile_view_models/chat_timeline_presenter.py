from __future__ import annotations

import json

from aipinho.schemas.interaction.contracts import ChatMessageRecord
from aipinho.schemas.mobile_view_models import ChatPresentationArtifact, ChatPresentationMessage, HumanizedCard, MobileChatPresentation
from aipinho.services.mobile_view_models.debug_details_renderer import DebugDetailsRenderer
from aipinho.services.mobile_view_models.human_card_renderer import HumanCardRenderer
from aipinho.services.mobile_view_models.mobile_sanitizer_service import MobileSanitizerService


class ChatTimelinePresenter:
    ROLE_LABELS = {
        "user": "Você",
        "assistant": "AIpinho",
        "speaker": "AIpinho",
        "system": "Sistema",
        "debugger": "Debugger",
    }

    def __init__(
        self,
        sanitizer: MobileSanitizerService | None = None,
        card_renderer: HumanCardRenderer | None = None,
        details_renderer: DebugDetailsRenderer | None = None,
    ) -> None:
        self.sanitizer = sanitizer or MobileSanitizerService()
        self.card_renderer = card_renderer or HumanCardRenderer(self.sanitizer)
        self.details_renderer = details_renderer or DebugDetailsRenderer()

    def present(self, *, session_id: str | None, messages: list[ChatMessageRecord], cards: list[HumanizedCard]) -> MobileChatPresentation:
        presentation_messages = [self._message(message) for message in messages if message.role in {"user", "assistant", "speaker"}]
        state_lines = self._state_lines(session_id=session_id, messages=messages, cards=cards)
        return MobileChatPresentation(
            messages=presentation_messages,
            state_lines=state_lines,
            details=self.details_renderer.details(messages=messages, cards=cards),
            raw_available=any(bool(message.raw_available or message.raw_ref) for message in messages),
            raw_default_visible=False,
            empty_state=None if presentation_messages else "Nenhuma mensagem nesta conversa ainda.",
        )

    def _message(self, message: ChatMessageRecord) -> ChatPresentationMessage:
        label = self.ROLE_LABELS.get(message.role, message.role)
        status = str(message.metadata.get("chat_response_status", "completed")) if message.role in {"assistant", "speaker"} else "completed"
        return ChatPresentationMessage(
            message_id=message.message_id,
            role=message.role,
            label=label,
            text=self.sanitizer.sanitize_text(message.content),
            created_at=message.created_at,
            status=status,
            task_id=message.task_id,
            safety_label=self._message_safety(message),
            copy_available=bool(message.copy_allowed),
            artifacts=self._message_artifacts(message),
        )

    def _message_artifacts(self, message: ChatMessageRecord) -> list[ChatPresentationArtifact]:
        if message.role not in {"assistant", "speaker"}:
            return []
        links = self._artifact_links(message)
        artifacts: list[ChatPresentationArtifact] = []
        for link in links:
            artifact_id = str(link.get("artifact_id") or "").strip()
            filename = str(link.get("filename") or "artifact").strip()
            content_type = str(link.get("content_type") or "application/octet-stream").strip()
            endpoint = str(link.get("download_endpoint") or link.get("download_path") or "").strip()
            if not artifact_id:
                artifacts.append(ChatPresentationArtifact(
                    artifact_id=None,
                    filename=filename,
                    content_type=content_type,
                    size_bytes=self._optional_int(link.get("size_bytes")),
                    download_endpoint=None,
                    label=f"{filename} indisponivel",
                    requires_token=True,
                    status="degraded",
                ))
                continue
            artifacts.append(ChatPresentationArtifact(
                artifact_id=artifact_id,
                filename=filename,
                content_type=content_type,
                size_bytes=self._optional_int(link.get("size_bytes")),
                download_endpoint=endpoint or f"/api/v1/artifacts/{artifact_id}/download",
                label=str(link.get("label") or f"Baixar {filename}"),
                requires_token=str(link.get("requires_token", "true")).lower() not in {"false", "0", "no", "nao"},
                status="ready",
            ))
        return artifacts

    def _artifact_links(self, message: ChatMessageRecord) -> list[dict[str, object]]:
        raw_links = message.metadata.get("artifact_links_json")
        if isinstance(raw_links, str) and raw_links.strip():
            try:
                parsed = json.loads(raw_links)
            except json.JSONDecodeError:
                parsed = []
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        artifact_id = str(message.metadata.get("artifact_id") or "").strip()
        if not artifact_id:
            return []
        return [{
            "artifact_id": artifact_id,
            "filename": message.metadata.get("artifact_filename") or "artifact",
            "content_type": message.metadata.get("artifact_content_type") or "application/octet-stream",
            "size_bytes": message.metadata.get("artifact_size_bytes"),
            "download_endpoint": message.metadata.get("artifact_download_endpoint") or message.metadata.get("artifact_download_path"),
            "label": f"Baixar {message.metadata.get('artifact_filename') or 'artifact'}",
            "requires_token": True,
        }]

    def _optional_int(self, value: object) -> int | None:
        try:
            text = str(value or "").strip()
            return int(text) if text else None
        except (TypeError, ValueError):
            return None

    def _message_safety(self, message: ChatMessageRecord) -> str:
        metadata = message.metadata
        status = str(metadata.get("chat_response_status", "")).lower()
        message_type = str(metadata.get("message_type", "")).lower()
        if status == "blocked" or message_type == "blocked_policy_message" or metadata.get("policy_block_reason_code"):
            return "Bloqueado"
        if status in {"degraded", "failed", "offline"}:
            return "Atenção"
        if str(metadata.get("approval_required", "False")).lower() == "true":
            return "Atenção"
        if str(metadata.get("rag_used", "False")).lower() == "true":
            return "Atenção"
        if str(metadata.get("fallback_used", "False")).lower() == "true":
            return "Atenção"
        return "Seguro"

    def _state_lines(self, *, session_id: str | None, messages: list[ChatMessageRecord], cards: list[HumanizedCard]) -> list[str]:
        latest = messages[-1] if messages else None
        metadata = latest.metadata if latest else {}
        operation_id = str(metadata.get("operation_id") or "").strip()
        operation_type = str(metadata.get("operation_type") or "").strip()
        operation_line = operation_type if operation_id else "Sem operacao"
        return [
            f"Sessão: {session_id or 'sem sessão'}",
            f"Mensagens: {len(messages)}",
            f"Task: {latest.task_id if latest and latest.task_id else 'Sem task'}",
            f"Operacao: {operation_line}",
            f"RAG: {self._yes_no(metadata.get('rag_used', False))}",
            f"Memória: {self._yes_no(metadata.get('memory_used', False))}",
            f"Approval: {self._yes_no(metadata.get('approval_required', False))}",
            f"Segurança: {self.details_renderer._safety(cards, metadata)}",
        ]

    def _yes_no(self, value: object) -> str:
        return "Sim" if str(value).lower() in {"true", "1", "yes", "sim"} else "Não"
