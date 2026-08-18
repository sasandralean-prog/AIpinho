from __future__ import annotations

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.schemas.chat.session_context import SessionContext
from aipinho.schemas.chat.session_state import SessionState


class SessionContextService:
    def build(self, request: ChatRequest, state: SessionState | None) -> SessionContext:
        if state is None:
            return SessionContext(current_message=request.message)
        recent = "\n".join(message.content for message in state.recent_messages[-3:])
        return SessionContext(
            current_message=request.message,
            recent_summary=recent,
            last_intent_type=state.last_intent_map.get("intent_type") if state.last_intent_map else None,
            last_workspace_candidate=state.active_workspace_candidate,
            active_task_draft_id=state.active_task_draft_id,
            warnings=list(state.warnings),
        )