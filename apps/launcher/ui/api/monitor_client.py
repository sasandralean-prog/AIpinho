from __future__ import annotations

from urllib.parse import urlparse, urlunparse

from apps.launcher.ui.api.base_client import BaseClient, ApiResult


class MonitorClient(BaseClient):
    allowed_restart_ports = {9088, 9089, 9098}
    blocked_restart_ports = {9099}

    def status(self) -> ApiResult: return self.get("/api/v1/monitor/status")
    def ports(self) -> ApiResult: return self.get("/api/v1/monitor/ports")
    def services(self) -> ApiResult: return self.get("/api/v1/monitor/services")
    def resources(self) -> ApiResult: return self.get("/api/v1/monitor/resources")
    def human_health(self) -> ApiResult: return self.get("/api/v1/monitor/human-health")

    def can_restart_port(self, port: int) -> bool:
        return port in self.allowed_restart_ports and port not in self.blocked_restart_ports

    def restart_service(self, service_id: str, port: int | None = None) -> ApiResult:
        if port is not None and not self.can_restart_port(port):
            return ApiResult(ok=False, status_code=409, data={"detail": "restart_blocked_by_launcher_policy"}, error="restart_blocked_by_launcher_policy")
        return self.post(f"/api/v1/monitor/services/{service_id}/restart", {})

    def restart_monitor_via_bootstrap(self) -> ApiResult:
        parsed = urlparse(self.base_url)
        netloc = parsed.hostname or "127.0.0.1"
        if parsed.username or parsed.password:
            auth = ""
            if parsed.username:
                auth += parsed.username
            if parsed.password:
                auth += f":{parsed.password}"
            netloc = f"{auth}@{netloc}"
        bootstrap_url = urlunparse((parsed.scheme or "http", f"{netloc}:9080", "", "", "", "")).rstrip("/")
        return BaseClient(bootstrap_url, token=self.token, timeout=self.timeout, transport=self.transport).post("/api/v1/bootstrap-control/monitor/restart", {})
