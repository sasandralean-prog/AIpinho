from __future__ import annotations

from aipinho.schemas.interaction.contracts import ChatMessageRecord
from aipinho.schemas.mobile_view_models import ChatPresentationDetail, HumanizedCard


class DebugDetailsRenderer:
    TECHNICAL_KEYS = {
        "session_id": "Sessao",
        "message_id": "Mensagem",
        "task_id": "Task",
        "approval_required": "Approval",
        "rag_used": "RAG",
        "memory_used": "Memória",
        "raw_available": "Raw",
        "fallback_used": "Fallback",
        "real_inference": "Inferencia real",
    }

    def details(self, *, messages: list[ChatMessageRecord], cards: list[HumanizedCard]) -> list[ChatPresentationDetail]:
        latest = messages[-1] if messages else None
        metadata = latest.metadata if latest else {}
        details = [
            ChatPresentationDetail(label="Task", value=self._task_value(latest)),
            ChatPresentationDetail(label="RAG", value=self._yes_no(metadata.get("rag_used", False))),
            ChatPresentationDetail(label="Memória", value=self._yes_no(metadata.get("memory_used", False))),
            ChatPresentationDetail(label="Approval", value=self._approval(metadata)),
            ChatPresentationDetail(label="Segurança", value=self._safety(cards, metadata)),
        ]
        if latest:
            for key, label in self.TECHNICAL_KEYS.items():
                if key in metadata and key not in {"task_id", "approval_required", "rag_used", "memory_used"}:
                    details.append(ChatPresentationDetail(label=label, value=self._format_value(metadata[key])))
        return details

    def _task_value(self, message: ChatMessageRecord | None) -> str:
        if not message or not message.task_id:
            return "Sem task"
        return message.task_id

    def _safety(self, cards: list[HumanizedCard], metadata: dict) -> str:
        status = str(metadata.get("status") or metadata.get("chat_response_status") or "").lower()
        message_type = str(metadata.get("message_type") or "").lower()
        if status == "pending_approval":
            return "Aguardando aprovação"
        if status == "failed":
            return "Falha operacional"
        if status == "degraded":
            return "Atenção: resposta degradada"
        block = metadata.get("policy_block") or metadata.get("block_cause")
        if status == "blocked" or message_type == "blocked_policy_message" or isinstance(block, dict):
            stage = str((block or {}).get("blocked_stage") or "policy").replace("_", " ")
            return f"Bloqueado por {stage}"
        if any(card.answers.is_it_safe.answer == "blocked" for card in cards):
            return "Bloqueado"
        if any(card.answers.is_it_safe.answer in {"caution", "risky"} for card in cards):
            return "Atenção"
        return "Seguro"

    @staticmethod
    def _approval(metadata: dict) -> str:
        if (
            metadata.get("approval_id")
            or DebugDetailsRenderer._is_truthy(metadata.get("approval_required"))
            or metadata.get("status") == "pending_approval"
        ):
            return "Necessário"
        return "Não"

    @staticmethod
    def _yes_no(value: object) -> str:
        return "Sim" if DebugDetailsRenderer._is_truthy(value) else "Não"

    @staticmethod
    def _is_truthy(value: object) -> bool:
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"true", "1", "yes", "sim"}

    def _format_value(self, value: object) -> str:
        if isinstance(value, bool):
            return self._yes_no(value)
        text = str(value)
        if text.lower() in {"true", "false"}:
            return self._yes_no(text)
        return text
