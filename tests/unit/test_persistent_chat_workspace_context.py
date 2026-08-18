from __future__ import annotations

from aipinho.schemas.interaction.contracts import ChatMessageRecord
from aipinho.services.chat.persistent_chat_workspace_context_service import PersistentChatWorkspaceContextService


def _message(role: str, content: str, metadata: dict[str, object] | None = None) -> ChatMessageRecord:
    return ChatMessageRecord(session_id="chat_test", role=role, content=content, metadata=metadata or {})


def test_persistent_chat_workspace_context_prefers_structured_workspace_path() -> None:
    messages = [
        _message("assistant", "Arquivo: C:\\Work\\Project\\reports\\health.md", {"file_path": "C:\\Work\\Project\\reports\\health.md"}),
        _message("assistant", "ok", {"workspace_path": "C:\\Work\\Project"}),
    ]

    assert PersistentChatWorkspaceContextService().from_messages(messages) == "C:\\Work\\Project"


def test_persistent_chat_workspace_context_recovers_from_latest_user_path() -> None:
    messages = [
        _message("user", "Use o workspace alvo C:\\Work\\Project com validacao."),
        _message("assistant", "Concluido."),
        _message("user", "Gere um relatorio em reports\\scan.md."),
    ]

    assert PersistentChatWorkspaceContextService().from_messages(messages) == "C:\\Work\\Project"
