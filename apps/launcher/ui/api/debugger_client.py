from __future__ import annotations

from apps.launcher.ui.api.base_client import BaseClient, ApiResult


class DebuggerClient(BaseClient):
    def status(self) -> ApiResult: return self.get("/api/v1/debugger/status")
    def events(self, query: str = "") -> ApiResult:
        suffix = f"?{query}" if query else ""
        return self.get(f"/api/v1/debugger/events{suffix}")
    def filters(self) -> ApiResult: return self.get("/api/v1/debugger/filters")
    def entity(self, entity_type: str, entity_id: str) -> ApiResult: return self.get(f"/api/v1/debugger/entities/{entity_type}/{entity_id}")
    def export_bundle(self, payload: dict[str, object]) -> ApiResult: return self.post("/api/v1/debugger/export", payload)
    def trace_timeline(self, trace_id: str) -> ApiResult: return self.get(f"/api/v1/debugger/traces/{trace_id}/timeline")
    def model_run(self, run_id: str) -> ApiResult: return self.get(f"/api/v1/debugger/model-runs/{run_id}")
    def role_run(self, run_id: str) -> ApiResult: return self.get(f"/api/v1/debugger/role-runs/{run_id}")
    def rag_run(self, query_id: str) -> ApiResult: return self.get(f"/api/v1/debugger/rag-runs/{query_id}")
