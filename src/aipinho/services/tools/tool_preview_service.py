from __future__ import annotations

from typing import Any

from aipinho.schemas.tools.tool_call import ToolCall
from aipinho.schemas.tools.tool_dry_run import ToolDryRunPlan
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.tools.tool_router import ToolRouter
from aipinho.services.tools.tool_trace_service import ToolTraceService


def _dump_model(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    if isinstance(value, dict):
        return value
    return {"value": str(value)}


class ToolPreviewService:
    def __init__(
        self,
        router: ToolRouter | None = None,
        draft_store: TaskDraftStore | None = None,
        preview_service: TaskPreviewService | None = None,
        approval_service: ApprovalService | None = None,
        trace: ToolTraceService | None = None,
    ) -> None:
        self.router = router or ToolRouter()
        self.draft_store = draft_store or TaskDraftStore()
        self.preview_service = preview_service or TaskPreviewService()
        self.approval_service = approval_service or ApprovalService()
        self.trace = trace or ToolTraceService()

    def plan_from_calls(self, calls: list[ToolCall], *, source: str = "direct") -> ToolDryRunPlan:
        return ToolDryRunPlan(
            source=source,  # type: ignore[arg-type]
            tool_calls=calls,
            safe_to_execute=False,
            safe_to_dry_run=True,
            trace=[self.trace.item(stage="tool_preview", rule="direct_calls", decision="planned", reason="direct_tool_calls_planned_without_execution", source="services/tools/tool_preview_service.py")],
        )

    def plan_from_draft(self, draft_id: str) -> ToolDryRunPlan | None:
        draft = self.draft_store.get(draft_id)
        if draft is None:
            return None
        calls = self._calls_for_actions(draft.requested_actions, draft_id=draft.draft_id, session_id=draft.session_id, workspace_path=draft.workspace.path)
        blocked = draft.status == "blocked" or draft.workspace.status == "protected"
        blocked_reasons = ["forbidden_root"] if draft.workspace.status == "protected" else (["blocked_draft"] if draft.status == "blocked" else [])
        return ToolDryRunPlan(
            source="draft",
            tool_calls=calls,
            policy_decision=dict(draft.policy_decision),
            workspace_status={"path": draft.workspace.path, "status": draft.workspace.status},
            safe_to_execute=False,
            safe_to_dry_run=not blocked,
            blocked=blocked,
            blocked_reasons=blocked_reasons,
            warnings=list(draft.warnings),
            trace=[self.trace.item(stage="tool_preview", rule="draft_to_tools", decision="blocked" if blocked else "planned", reason="draft_actions_mapped_to_tool_calls", source="TaskContractDraft", data={"draft_id": draft.draft_id, "actions": draft.requested_actions})],
        )

    def plan_from_preview(self, preview_id: str) -> ToolDryRunPlan | None:
        preview = self.preview_service.get_preview(preview_id)
        if preview is None:
            return None
        calls = self._calls_for_actions(preview.requested_actions, draft_id=preview.draft_id, preview_id=preview.preview_id, session_id=preview.session_id)
        blocked = preview.status == "blocked"
        return ToolDryRunPlan(
            source="preview",
            tool_calls=calls,
            policy_decision={"policy_snapshot": _dump_model(preview.policy_snapshot)},
            workspace_status={"status": preview.policy_snapshot.workspace_status},
            safe_to_execute=False,
            safe_to_dry_run=not blocked,
            blocked=blocked,
            blocked_reasons=["blocked_preview"] if blocked else [],
            warnings=list(preview.warnings),
            trace=[self.trace.item(stage="tool_preview", rule="preview_to_tools", decision="blocked" if blocked else "planned", reason="preview_actions_mapped_to_tool_calls", source="TaskPreview", data={"preview_id": preview.preview_id, "actions": preview.requested_actions})],
        )

    def _calls_for_actions(
        self,
        actions: list[str],
        *,
        draft_id: str | None = None,
        preview_id: str | None = None,
        session_id: str | None = None,
        workspace_path: str | None = None,
    ) -> list[ToolCall]:
        calls: list[ToolCall] = []
        for action in actions:
            tool = self.router.primary_tool_for_action(action)
            if tool is None:
                calls.append(ToolCall(tool_id=f"unknown.action.{action}", input={}, draft_id=draft_id, preview_id=preview_id, session_id=session_id))
                continue
            calls.append(ToolCall(
                tool_id=tool.tool_id,
                input=self._input_for_action(action, workspace_path=workspace_path, draft_id=draft_id, preview_id=preview_id),
                draft_id=draft_id,
                preview_id=preview_id,
                session_id=session_id,
                mode="dry_run",
            ))
        return calls

    def _input_for_action(self, action: str, *, workspace_path: str | None, draft_id: str | None, preview_id: str | None) -> dict[str, object]:
        path = workspace_path or "contract_path_unavailable"
        if action == "read_files":
            return {"workspace": path, "path": "."}
        if action == "list_directory":
            return {"workspace": path, "path": "."}
        if action == "inspect_path":
            return {"workspace": path, "path": "."}
        if action == "read_config":
            return {"workspace": path, "path": "config/app/identity.yaml"}
        if action == "write_files":
            return {"path": path, "content_preview": "dry-run content preview only; not written"}
        if action == "patch_preview":
            return {"summary": "dry-run would prepare patch preview only"}
        if action == "apply_patch":
            return {"patch_preview_id": preview_id or draft_id or "preview_unavailable"}
        if action == "run_command":
            return {"command": "<planned command would be shown here; not executed>"}
        if action == "git_status":
            return {"workspace": path}
        if action == "git_commit":
            return {"message": "dry-run commit message only"}
        return {}

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "tool_preview", "real_execution_enabled": False}
