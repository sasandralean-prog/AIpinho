from __future__ import annotations

from apps.launcher.ui.api.base_client import BaseClient, ApiResult


class ChatClient(BaseClient):
    def list_sessions(self) -> ApiResult: return self.get("/api/v1/chat/sessions")
    def create_session(self, title: str = "Nova conversa") -> ApiResult: return self.post("/api/v1/chat/sessions", {"title": title})
    def rename_session(self, session_id: str, title: str) -> ApiResult: return self.patch(f"/api/v1/chat/sessions/{session_id}", {"title": title})
    def delete_session(self, session_id: str) -> ApiResult: return self.delete(f"/api/v1/chat/sessions/{session_id}")
    def timeline(self, session_id: str) -> ApiResult: return self.get(f"/api/v1/chat/sessions/{session_id}/timeline")
    def record_message(self, session_id: str, content: str, metadata: dict[str, object] | None = None) -> ApiResult:
        return self.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            {"role": "user", "content": content, "metadata": metadata or {}},
        )

    def send_message(self, session_id: str, content: str, metadata: dict[str, object] | None = None) -> ApiResult:
        return self.post(
            f"/api/v1/chat/sessions/{session_id}/send",
            {"role": "user", "content": content, "metadata": metadata or {}},
        )
    def copy_message(self, message_id: str) -> ApiResult: return self.get(f"/api/v1/chat/messages/{message_id}/copy")
    def raw(self, message_id: str) -> ApiResult: return self.get(f"/api/v1/chat/messages/{message_id}/raw")
    def speaker_updates(self, task_id: str, after_event_id: str | None = None) -> ApiResult:
        suffix = f"?after_event_id={after_event_id}" if after_event_id else ""
        return self.get(f"/api/v1/task-runs/{task_id}/speaker/updates{suffix}")
    def feedback(self, message_id: str, rating: str, reason: str | None = None) -> ApiResult:
        return self.post(f"/api/v1/chat/messages/{message_id}/feedback", {"target_type": "chat_message", "target_id": message_id, "rating": rating, "reason": reason})
