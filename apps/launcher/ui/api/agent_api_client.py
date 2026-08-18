from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from apps.launcher.ui.api.base_client import ApiResult, BaseClient


@dataclass(frozen=True)
class AgentEndpointConfig:
    agent_id: str
    display_name: str
    route_prefix: str
    operation_type: str
    provider_label: str
    supports_plan: bool = True
    supports_preview: bool = True
    supports_route_preview: bool = False
    external_provider_notice: str | None = None


class DesktopAgentApiClient(BaseClient):
    def __init__(self, base_url: str, config: AgentEndpointConfig, **kwargs) -> None:
        super().__init__(base_url, **kwargs)
        self.config = config

    def health(self) -> ApiResult:
        return self.get(f"{self.config.route_prefix}/health")

    def config_status(self) -> ApiResult:
        return self.get(f"{self.config.route_prefix}/config/status")

    def sessions(self) -> ApiResult:
        return self.get(f"{self.config.route_prefix}/sessions")

    def create_session(self, title: str | None = None) -> ApiResult:
        return self.post(
            f"{self.config.route_prefix}/sessions",
            {"title": title or self.config.display_name},
        )

    def rename_session(self, session_id: str, title: str) -> ApiResult:
        path = f"{self.config.route_prefix}/sessions/{quote(session_id, safe='')}"
        if self.config.agent_id == "lucio":
            return self.patch(path, {"title": title})
        return self.post(f"{path}/rename", {"title": title})

    def delete_session(self, session_id: str) -> ApiResult:
        return self.delete(f"{self.config.route_prefix}/sessions/{quote(session_id, safe='')}")

    def messages(self, session_id: str) -> ApiResult:
        return self.get(f"{self.config.route_prefix}/sessions/{quote(session_id, safe='')}/messages")

    def send(
        self,
        session_id: str,
        prompt: str,
        workspace_context: str = "",
        artifact_ids: list[str] | None = None,
    ) -> ApiResult:
        return self.post(
            f"{self.config.route_prefix}/sessions/{quote(session_id, safe='')}/send",
            self._payload(
                session_id,
                prompt,
                workspace_context,
                self.config.operation_type,
                [],
                artifact_ids or [],
            ),
        )

    def plan(self, session_id: str, prompt: str, workspace_context: str = "") -> ApiResult:
        return self.post(
            f"{self.config.route_prefix}/sessions/{quote(session_id, safe='')}/plan",
            self._payload(
                session_id,
                prompt,
                workspace_context,
                f"{self.config.agent_id}_plan",
                ["read_workspace", "scan_workspace"] if workspace_context else [],
                [],
            ),
        )

    def preview(self, session_id: str, prompt: str, workspace_context: str = "") -> ApiResult:
        return self.post(
            f"{self.config.route_prefix}/sessions/{quote(session_id, safe='')}/preview",
            self._payload(
                session_id,
                prompt,
                workspace_context,
                f"{self.config.agent_id}_patch_preview",
                ["read_workspace", "scan_workspace", "create_patch_preview"],
                [],
            ),
        )

    def route_preview(
        self,
        session_id: str,
        prompt: str,
        workspace_context: str = "",
        artifact_ids: list[str] | None = None,
    ) -> ApiResult:
        return self.post(
            f"{self.config.route_prefix}/sessions/{quote(session_id, safe='')}/route-preview",
            self._payload(
                session_id,
                prompt,
                workspace_context,
                self.config.operation_type,
                [],
                artifact_ids or [],
            ),
        )

    def view_model(
        self,
        session_id: str,
        after_event_id: str | None = None,
        mode: str = "normal",
    ) -> ApiResult:
        query: list[str] = []
        if after_event_id:
            query.append(f"after_event_id={quote(after_event_id, safe='')}")
        if self.config.agent_id == "lucio":
            query.append(f"mode={quote(mode, safe='')}")
        suffix = f"?{'&'.join(query)}" if query else ""
        return self.get(
            f"{self.config.route_prefix}/sessions/{quote(session_id, safe='')}/view-model{suffix}"
        )

    def cancel_run(self, run_id: str) -> ApiResult:
        return self.post(f"{self.config.route_prefix}/runs/{quote(run_id, safe='')}/cancel")

    def artifacts(self, session_id: str) -> ApiResult:
        return self.get(
            f"/api/v1/agents/{quote(self.config.agent_id, safe='')}/sessions/"
            f"{quote(session_id, safe='')}/artifacts"
        )

    def _payload(
        self,
        session_id: str,
        prompt: str,
        workspace_context: str,
        operation_type: str,
        capabilities: list[str],
        artifact_ids: list[str],
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "session_id": session_id,
            "prompt": prompt,
            "operation_type": operation_type,
            "requested_capabilities": capabilities,
        }
        if self.config.agent_id == "lucio":
            payload["workspace_id"] = workspace_context or None
            payload["artifacts"] = [
                {"artifact_id": artifact_id, "purpose": "evidence"}
                for artifact_id in artifact_ids
            ]
        else:
            payload["workspace_context"] = workspace_context or None
        return payload
