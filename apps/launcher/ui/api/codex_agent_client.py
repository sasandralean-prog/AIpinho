from __future__ import annotations

from apps.launcher.ui.api.base_client import BaseClient


class CodexAgentClient(BaseClient):
    def health(self):
        return self.get("/api/v1/codex-agent/health")

    def config_status(self):
        return self.get("/api/v1/codex-agent/config/status")

    def sessions(self):
        return self.get("/api/v1/codex-agent/sessions")

    def create_session(self, title: str = "Codex Agent"):
        return self.post("/api/v1/codex-agent/sessions", {"title": title})

    def messages(self, session_id: str):
        return self.get(f"/api/v1/codex-agent/sessions/{session_id}/messages")

    def rename_session(self, session_id: str, title: str):
        return self.post(f"/api/v1/codex-agent/sessions/{session_id}/rename", {"title": title})

    def delete_session(self, session_id: str):
        return self.delete(f"/api/v1/codex-agent/sessions/{session_id}")

    def send(self, session_id: str, prompt: str, workspace_context: str = "", capabilities: list[str] | None = None):
        return self.post(
            f"/api/v1/codex-agent/sessions/{session_id}/send",
            {
                "session_id": session_id,
                "prompt": prompt,
                "workspace_context": workspace_context or None,
                "operation_type": "codex_chat",
                "requested_capabilities": capabilities or [],
            },
        )

    def plan(self, session_id: str, prompt: str, workspace_context: str = ""):
        return self.post(
            f"/api/v1/codex-agent/sessions/{session_id}/plan",
            {
                "session_id": session_id,
                "prompt": prompt,
                "workspace_context": workspace_context or None,
                "operation_type": "codex_plan",
                "requested_capabilities": ["read_workspace", "scan_workspace"] if workspace_context else [],
            },
        )

    def preview(self, session_id: str, prompt: str, workspace_context: str = ""):
        return self.post(
            f"/api/v1/codex-agent/sessions/{session_id}/preview",
            {
                "session_id": session_id,
                "prompt": prompt,
                "workspace_context": workspace_context or None,
                "operation_type": "codex_patch_preview",
                "requested_capabilities": ["read_workspace", "scan_workspace", "create_patch_preview"],
            },
        )

