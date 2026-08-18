from __future__ import annotations

from typing import Any
from uuid import uuid4

from aipinho.schemas.tools.read_only_execution import ReadOnlyExecutionBundle
from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.schemas.tools.tool_execution_result import ToolExecutionResult
from aipinho.services.orchestration.task_draft_store import TaskDraftStore
from aipinho.services.orchestration.task_preview_service import TaskPreviewService
from aipinho.services.tools.execution_audit_service import ExecutionAuditService
from aipinho.services.tools.filesystem_read_service import FilesystemReadService
from aipinho.services.tools.tool_execution_guard import ToolExecutionGuard
from aipinho.services.tools.tool_preview_service import ToolPreviewService


class ReadOnlyExecutionService:
    def __init__(self, guard: ToolExecutionGuard | None = None, filesystem: FilesystemReadService | None = None, audit: ExecutionAuditService | None = None, preview_service: ToolPreviewService | None = None, draft_store: TaskDraftStore | None = None, task_preview_service: TaskPreviewService | None = None) -> None:
        self.guard = guard or ToolExecutionGuard()
        self.filesystem = filesystem or FilesystemReadService(path_guard=self.guard.path_guard)
        self.audit = audit or ExecutionAuditService()
        self.preview_service = preview_service or ToolPreviewService()
        self.draft_store = draft_store or TaskDraftStore()
        self.task_preview_service = task_preview_service or TaskPreviewService()

    def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        execution_id = f"exec_{uuid4().hex}"
        decision, tool, context = self.guard.check(request)
        if tool is None or not decision.allowed:
            result = ToolExecutionResult(execution_id=execution_id, tool_id=request.tool_id, status="blocked" if decision.status != "invalid" else "invalid", action=tool.action if tool else None, capability=tool.capability if tool else None, workspace=decision.workspace, target_path=decision.target_path, warnings=list(decision.warnings), violations=list(decision.violations), trace=list(decision.trace), side_effects=False, safe_to_execute=False)
            event = self.audit.record(result, policy_decision_id=self._policy_decision_id(context))
            result.audit_event_id = event.audit_event_id
            return result

        if tool.tool_id in {"filesystem.inspect_path", "config.read"} or tool.action in {"inspect_path", "read_config"}:
            result = self.filesystem.inspect_path(request, execution_id=execution_id, action=tool.action, capability=tool.capability)
        elif tool.tool_id == "filesystem.list_directory" or tool.action == "list_directory":
            result = self.filesystem.list_directory(request, execution_id=execution_id, action=tool.action, capability=tool.capability)
        elif tool.tool_id == "filesystem.read_file" or tool.action == "read_files":
            result = self.filesystem.read_file(request, execution_id=execution_id, action=tool.action, capability=tool.capability)
        else:
            result = ToolExecutionResult(execution_id=execution_id, tool_id=request.tool_id, status="blocked", action=tool.action, capability=tool.capability, workspace=decision.workspace, target_path=decision.target_path, violations=["adapter_not_allowed_for_readonly_execution"], side_effects=False, safe_to_execute=False)
        result.trace = [*decision.trace, *result.trace]
        result.warnings = list(dict.fromkeys([*decision.warnings, *result.warnings]))
        event = self.audit.record(result, policy_decision_id=self._policy_decision_id(context))
        result.audit_event_id = event.audit_event_id
        return result

    def execute_many(self, requests: list[ToolExecutionRequest]) -> ReadOnlyExecutionBundle:
        results = [self.execute(request) for request in requests]
        statuses = {item.status for item in results}
        if not results:
            status = "invalid"
        elif len(statuses) == 1:
            status = next(iter(statuses))
        elif "executed_readonly" in statuses and any(item in statuses for item in {"blocked", "invalid", "degraded"}):
            status = "mixed"
        elif "blocked" in statuses:
            status = "blocked"
        else:
            status = "mixed"
        warnings = []
        for result in results:
            warnings.extend(result.warnings)
        return ReadOnlyExecutionBundle(status=status, results=results, warnings=list(dict.fromkeys(warnings)))  # type: ignore[arg-type]

    def execute_from_draft(self, draft_id: str, tool_inputs: list[dict[str, Any]] | None = None) -> ReadOnlyExecutionBundle | None:
        draft = self.draft_store.get(draft_id)
        if draft is None:
            return None
        requests = self._requests_from_inputs(tool_inputs, draft_id=draft_id, session_id=draft.session_id, default_workspace=draft.workspace.path)
        if not requests:
            plan = self.preview_service.plan_from_draft(draft_id)
            requests = [self._request_from_tool_call(call, default_workspace=draft.workspace.path) for call in (plan.tool_calls if plan else [])]
        return self.execute_many(requests)

    def execute_from_preview(self, preview_id: str, tool_inputs: list[dict[str, Any]] | None = None) -> ReadOnlyExecutionBundle | None:
        preview = self.task_preview_service.get_preview(preview_id)
        if preview is None:
            return None
        draft = self.draft_store.get(preview.draft_id)
        default_workspace = draft.workspace.path if draft is not None else None
        requests = self._requests_from_inputs(tool_inputs, preview_id=preview_id, draft_id=preview.draft_id, session_id=preview.session_id, default_workspace=default_workspace)
        if not requests:
            plan = self.preview_service.plan_from_preview(preview_id)
            requests = [self._request_from_tool_call(call, default_workspace=default_workspace) for call in (plan.tool_calls if plan else [])]
        return self.execute_many(requests)

    def _requests_from_inputs(self, tool_inputs: list[dict[str, Any]] | None, *, draft_id: str | None = None, preview_id: str | None = None, session_id: str | None = None, default_workspace: str | None = None) -> list[ToolExecutionRequest]:
        requests: list[ToolExecutionRequest] = []
        for item in tool_inputs or []:
            if not isinstance(item, dict):
                continue
            data = dict(item.get("input", {}) if isinstance(item.get("input", {}), dict) else {})
            if default_workspace and not data.get("workspace"):
                data["workspace"] = default_workspace
            requests.append(ToolExecutionRequest(tool_id=str(item.get("tool_id", "")), input=data, draft_id=draft_id, preview_id=preview_id, session_id=session_id, mode="readonly", include_content=bool(item.get("include_content", True)), include_trace=bool(item.get("include_trace", False))))
        return requests

    def _request_from_tool_call(self, call, *, default_workspace: str | None) -> ToolExecutionRequest:
        data = dict(call.input)
        if default_workspace and not data.get("workspace"):
            data["workspace"] = default_workspace
        if data.get("workspace") and not data.get("path"):
            data["path"] = "."
        return ToolExecutionRequest(tool_id=call.tool_id, input=data, draft_id=call.draft_id, preview_id=call.preview_id, session_id=call.session_id, mode="readonly")

    def _policy_decision_id(self, context: dict[str, Any]) -> str | None:
        policy = context.get("policy_decision", {}) if isinstance(context, dict) else {}
        if isinstance(policy, dict):
            return str(policy.get("decision_id") or policy.get("policy_decision_id") or "") or None
        return None

    def get_execution(self, execution_id: str) -> ToolExecutionResult | None:
        return self.audit.get_result(execution_id)

    def get_events(self, execution_id: str):
        return self.audit.get_events(execution_id)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "read_only_execution", "read_only_execution_enabled": True, "real_execution_enabled": True, "write_execution_enabled": False, "shell_execution_enabled": False, "patch_apply_enabled": False, "git_write_enabled": False, "memory_write_enabled": False, "rag_query_enabled": False, "llm_enabled": False, "guard": self.guard.status(), "audit": self.audit.status()}
