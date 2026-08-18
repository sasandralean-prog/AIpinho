from __future__ import annotations

from apps.launcher.ui.api.base_client import ApiResult, BaseClient


class GovernanceClient(BaseClient):
    def health(self) -> ApiResult:
        return self.get("/api/v1/config/health")

    def effective_policy(self) -> ApiResult:
        return self.get("/api/v1/config/effective-policy")

    def workspaces(self) -> ApiResult:
        return self.get("/api/v1/config/workspaces")

    def workspace_roles(self) -> ApiResult:
        return self.get("/api/v1/config/workspace-roles")

    def permission_matrix(self) -> ApiResult:
        return self.get("/api/v1/config/permission-matrix")

    def providers(self) -> ApiResult:
        return self.get("/api/v1/config/providers")

    def agents(self) -> ApiResult:
        return self.get("/api/v1/config/agents")

    def changes(self) -> ApiResult:
        return self.get("/api/v1/config/changes")

    def backups(self) -> ApiResult:
        return self.get("/api/v1/config/backups")

    def preview_workspace(self, workspace_id: str, path: str, role: str) -> ApiResult:
        return self.post(
            "/api/v1/config/workspaces/preview",
            {"workspace_id": workspace_id, "path": path, "role": role},
        )

    def create_workspace(
        self,
        *,
        workspace_id: str,
        root_path: str,
        role: str,
        human_label: str = "",
        permissions: dict[str, str] | None = None,
    ) -> ApiResult:
        return self.post(
            "/api/v1/config/workspaces",
            {
                "workspace_id": workspace_id,
                "root_path": root_path,
                "role": role,
                "human_label": human_label,
                "reason": "launcher_governance_console_workspace_change",
                "approval_required": True,
                "enabled": True,
                "permissions": permissions or {},
                "evidence": ["launcher_governance_console"],
            },
        )

    def approve_change(self, change_id: str) -> ApiResult:
        return self.post(f"/api/v1/config/changes/{change_id}/approve")

    def apply_change(self, change_id: str) -> ApiResult:
        return self.post(f"/api/v1/config/changes/{change_id}/apply")

    def cancel_change(self, change_id: str) -> ApiResult:
        return self.post(f"/api/v1/config/changes/{change_id}/cancel")

    def rollback(self, backup_id: str) -> ApiResult:
        return self.post(f"/api/v1/config/rollback/{backup_id}")

    def flow_rules(self) -> ApiResult:
        return self.get("/api/v1/workspace-flows/rules")

    def flow_plan(self, payload: dict[str, object]) -> ApiResult:
        return self.post("/api/v1/workspace-flows/plan", payload)

    def flow_plan_detail(self, flow_plan_id: str) -> ApiResult:
        return self.get(f"/api/v1/workspace-flows/plans/{flow_plan_id}")

    def approve_flow_plan(self, flow_plan_id: str) -> ApiResult:
        return self.post(f"/api/v1/workspace-flows/plans/{flow_plan_id}/approve")

    def deny_flow_plan(self, flow_plan_id: str) -> ApiResult:
        return self.post(f"/api/v1/workspace-flows/plans/{flow_plan_id}/deny")

    def execute_flow_plan(self, flow_plan_id: str) -> ApiResult:
        return self.post(f"/api/v1/workspace-flows/plans/{flow_plan_id}/execute")
