from __future__ import annotations

from apps.launcher.ui.api.base_client import ApiResult, BaseClient


class UniversalApproverClient(BaseClient):
    def list_approvers(self) -> ApiResult:
        return self.get("/api/v1/universal-approvers")

    def mobile_view(self) -> ApiResult:
        return self.get("/api/v1/universal-approvers/mobile-view")

    def timeline(self, limit: int = 100) -> ApiResult:
        return self.get(f"/api/v1/universal-approvers/approval-timeline?limit={limit}")

    def text_decision(
        self,
        approval_id: str,
        *,
        approver_id: str,
        text: str,
        requested_by: str = "launcher",
        reason: str = "",
    ) -> ApiResult:
        return self.post(
            f"/api/v1/universal-approvers/approvals/{approval_id}/text-decision",
            {
                "approver_id": approver_id,
                "text": text,
                "requested_by": requested_by,
                "reason": reason,
                "metadata": {"source_channel": "launcher"},
            },
        )
