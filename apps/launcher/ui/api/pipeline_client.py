from __future__ import annotations

from urllib.parse import quote

from apps.launcher.ui.api.base_client import BaseClient, ApiResult


class PipelineClient(BaseClient):
    def mobile_pipeline(self, task_id: str | None = None) -> ApiResult:
        if task_id:
            return self.get(f"/api/v1/mobile/view-model/pipeline/{quote(task_id, safe='')}")
        return self.get("/api/v1/mobile/view-model/pipeline")

    # Compat endpoints: kept for old diagnostics, no longer the Launcher source of truth.
    def task_cards(self) -> ApiResult: return self.get("/api/v1/tasks/cards")
    def task_timeline(self, task_id: str) -> ApiResult: return self.get(f"/api/v1/tasks/{quote(task_id, safe='')}/timeline")
    def pipeline_card(self, task_id: str) -> ApiResult: return self.get(f"/api/v1/pipeline/cards/{quote(task_id, safe='')}")

    def pending_approvals(self) -> ApiResult: return self.get("/api/v1/approvals/pending")
    def task_approvals(self, task_id: str) -> ApiResult: return self.get(f"/api/v1/tasks/{quote(task_id, safe='')}/approvals")
    def cancel_task(self, task_id: str, reason: str = "launcher_desktop_task_cancelled") -> ApiResult:
        return self.post(
            f"/api/v1/task-runs/{quote(task_id, safe='')}/cancel",
            {"reason": reason, "requested_by": {"type": "human", "id": "launcher_desktop"}},
        )
    def retry_node(self, task_id: str, node_id: str, reason: str = "launcher_retry_node") -> ApiResult:
        return self.post(
            f"/api/v1/task-runs/{quote(task_id, safe='')}/execution-graph/nodes/{quote(node_id, safe='')}/retry",
            {"reason": reason},
        )
    def cancel_node(self, task_id: str, node_id: str, reason: str = "launcher_cancel_node") -> ApiResult:
        return self.post(
            f"/api/v1/task-runs/{quote(task_id, safe='')}/execution-graph/nodes/{quote(node_id, safe='')}/cancel",
            {"reason": reason},
        )
    def planning_report(self, task_id: str) -> ApiResult:
        return self.get(f"/api/v1/task-runs/{quote(task_id, safe='')}/planning/report")
    def replan_node(self, task_id: str, node_id: str, reason: str = "launcher_replan_node") -> ApiResult:
        return self.post(
            f"/api/v1/task-runs/{quote(task_id, safe='')}/planning/nodes/{quote(node_id, safe='')}/replan",
            {"reason": reason},
        )
    def approve_safe_batch(self, task_id: str, reason: str = "launcher_safe_batch_approved") -> ApiResult:
        return self.post(f"/api/v1/tasks/{quote(task_id, safe='')}/approvals/approve-safe-batch", {"actor": {"type": "human", "id": "launcher_desktop"}, "reason": reason})
    def deny_safe_batch(self, task_id: str, reason: str = "launcher_safe_batch_denied") -> ApiResult:
        return self.post(f"/api/v1/tasks/{quote(task_id, safe='')}/approvals/deny-safe-batch", {"actor": {"type": "human", "id": "launcher_desktop"}, "reason": reason})
    def approve(self, approval_id: str, reason: str = "launcher_desktop_user_approved") -> ApiResult:
        return self.post(f"/api/v1/approvals/{quote(approval_id, safe='')}/approve", {"actor": {"type": "human", "id": "launcher_desktop"}, "reason": reason})
    def reject(self, approval_id: str, reason: str = "launcher_desktop_user_rejected") -> ApiResult:
        return self.post(f"/api/v1/approvals/{quote(approval_id, safe='')}/reject", {"actor": {"type": "human", "id": "launcher_desktop"}, "reason": reason})
    def cancel(self, approval_id: str, reason: str = "launcher_desktop_user_cancelled") -> ApiResult:
        return self.post(f"/api/v1/approvals/{quote(approval_id, safe='')}/cancel", {"actor": {"type": "human", "id": "launcher_desktop"}, "reason": reason})
