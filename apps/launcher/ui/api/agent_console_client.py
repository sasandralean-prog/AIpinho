from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from apps.launcher.ui.api.base_client import ApiResult, BaseClient


class AgentConsoleClient(BaseClient):
    def bridge_status(self) -> ApiResult:
        return self.get("/api/v1/agent-bridge/status")

    def bridge_active(self) -> ApiResult:
        return self.get("/api/v1/agent-bridge/active")

    def bridge_details(self, bridge_task_id: str) -> ApiResult:
        return self.get(f"/api/v1/agent-bridge/tasks/{quote(bridge_task_id, safe='')}/details")

    def bridge_cancel(self, bridge_task_id: str) -> ApiResult:
        return self.post(f"/api/v1/agent-bridge/tasks/{quote(bridge_task_id, safe='')}/cancel")

    def artifacts(self) -> ApiResult:
        return self.get("/api/v1/artifacts?limit=100")

    def traces_recent(self) -> ApiResult:
        return self.get("/api/v1/debugger/recent?limit=50")

    def trace_by_bridge_task(self, bridge_task_id: str) -> ApiResult:
        return self.get(f"/api/v1/debugger/by-bridge-task/{quote(bridge_task_id, safe='')}")

    def trace_by_agent(self, agent_id: str) -> ApiResult:
        return self.get(f"/api/v1/debugger/by-agent/{quote(agent_id, safe='')}?limit=50")

    def trace_export(self, trace_id: str, format: str = "markdown") -> ApiResult:
        return self.post(f"/api/v1/debugger/traces/{quote(trace_id, safe='')}/export", {"format": format})

    def artifact_revalidate(self, artifact_id: str) -> ApiResult:
        return self.post(f"/api/v1/artifacts/{quote(artifact_id, safe='')}/revalidate")

    def artifact_provenance(self, artifact_id: str) -> ApiResult:
        return self.get(f"/api/v1/artifacts/{quote(artifact_id, safe='')}/provenance")

    def artifact_download(self, artifact_id: str, endpoint: str | None = None) -> ApiResult:
        if endpoint:
            path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
            return self.get(path)
        return self.get(f"/api/v1/artifacts/{quote(artifact_id, safe='')}/download")

    def save_download(self, result: ApiResult, target: Path) -> bool:
        if not result.ok:
            return False
        data = result.data if isinstance(result.data, (bytes, bytearray)) else str(result.data).encode("utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bytes(data))
        return True

    def approvals_pending(self) -> ApiResult:
        return self.get("/api/v1/approvals/pending")

    def approve(self, approval_id: str) -> ApiResult:
        return self.post(f"/api/v1/approvals/{quote(approval_id, safe='')}/approve", {"reason": "launcher_agent_console"})

    def deny(self, approval_id: str) -> ApiResult:
        return self.post(f"/api/v1/approvals/{quote(approval_id, safe='')}/deny", {"reason": "launcher_agent_console"})

    def locks(self) -> ApiResult:
        return self.get("/api/v1/locks")

    def release_lock(self, lock_id: str) -> ApiResult:
        return self.post(f"/api/v1/locks/{quote(lock_id, safe='')}/release", {"actor_agent": "launcher", "reason": "released_from_agent_console"})

    def override_lock(self, lock_id: str) -> ApiResult:
        return self.post(f"/api/v1/locks/{quote(lock_id, safe='')}/override", {"actor_agent": "launcher", "reason": "manual_override_from_agent_console"})
