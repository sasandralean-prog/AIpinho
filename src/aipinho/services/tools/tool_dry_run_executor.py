from __future__ import annotations

from aipinho.adapters.android.android_tool_adapter import AndroidToolAdapter
from aipinho.adapters.filesystem.filesystem_tool_adapter import FilesystemToolAdapter
from aipinho.adapters.git.git_tool_adapter import GitToolAdapter
from aipinho.adapters.shell.shell_tool_adapter import ShellToolAdapter
from aipinho.adapters.web.web_tool_adapter import WebToolAdapter
from aipinho.schemas.tools.tool_dry_run import ToolDryRunPlan, ToolDryRunResult
from aipinho.schemas.tools.tool_result import ToolDryRunResultItem
from aipinho.services.tools.tool_safety_service import ToolSafetyService
from aipinho.services.tools.tool_trace_service import ToolTraceService


class ToolDryRunExecutor:
    def __init__(self, safety: ToolSafetyService | None = None, trace: ToolTraceService | None = None) -> None:
        self.safety = safety or ToolSafetyService()
        self.trace = trace or ToolTraceService()
        self.adapters = {
            "filesystem": FilesystemToolAdapter(),
            "shell": ShellToolAdapter(),
            "git": GitToolAdapter(),
            "android": AndroidToolAdapter(),
            "web": WebToolAdapter(),
        }

    def dry_run(self, plan: ToolDryRunPlan) -> ToolDryRunResult:
        trace = list(plan.trace)
        warnings = list(plan.warnings)
        if plan.blocked:
            trace.append(self.trace.item(stage="tool_dry_run", rule="plan_blocked", decision="blocked", reason="dry_run_plan_blocked_before_adapter", severity="error", source="ToolDryRunPlan", data={"blocked_reasons": plan.blocked_reasons}))
            return ToolDryRunResult(
                dry_run_id=plan.dry_run_id,
                status="blocked",
                tool_results=[],
                safe_to_execute=False,
                summary="Dry-run blocked before simulation; not executed and no side effects reais occurred.",
                warnings=warnings,
                trace=trace,
            )

        items: list[ToolDryRunResultItem] = []
        for call in plan.tool_calls:
            safety, tool, context = self.safety.check(call)
            trace.extend(safety.trace)
            warnings.extend(safety.warnings)
            if tool is None:
                items.append(ToolDryRunResultItem(
                    tool_id=call.tool_id,
                    status="blocked",
                    would_do="Unknown tool would not be simulated; not executed.",
                    input_valid=False,
                    warnings=list(safety.warnings),
                    trace=list(safety.trace),
                ))
                continue
            if safety.blocked or safety.status in {"blocked", "invalid"}:
                items.append(ToolDryRunResultItem(
                    tool_id=tool.tool_id,
                    status="blocked" if safety.status == "blocked" else "invalid",
                    would_do=f"Dry-run blocked for {tool.tool_id}: {', '.join(safety.blocked_reasons) or safety.status}. Not executed.",
                    would_use_actions=[tool.action],
                    would_require_capabilities=[tool.capability],
                    would_require_approval=list(safety.approval_required_for),
                    potential_side_effects=[tool.action] if tool.side_effect else [],
                    input_valid=False,
                    warnings=list(safety.warnings),
                    trace=list(safety.trace),
                ))
                continue
            adapter = self.adapters.get(tool.adapter)
            if adapter is None:
                items.append(ToolDryRunResultItem(
                    tool_id=tool.tool_id,
                    status="degraded",
                    would_do=f"No adapter available for {tool.adapter}; not executed.",
                    input_valid=True,
                    warnings=[*safety.warnings, "adapter_missing"],
                    trace=list(safety.trace),
                ))
                continue
            item = adapter.dry_run(tool, call, safety)
            items.append(item)
            if context.get("approval_snapshot"):
                trace.append(self.trace.item(stage="tool_dry_run", rule="approval_snapshot", decision="noted", reason="approval_loaded_for_trace_only_no_execution", source="ApprovalService", data={"approval_status": context["approval_snapshot"].get("status")}))

        status = self._overall_status(items)
        summary = self._summary(status, items)
        return ToolDryRunResult(
            dry_run_id=plan.dry_run_id,
            status=status,
            tool_results=items,
            safe_to_execute=False,
            summary=summary,
            warnings=list(dict.fromkeys(warnings)),
            trace=trace,
        )

    def _overall_status(self, items: list[ToolDryRunResultItem]):
        if not items:
            return "invalid"
        statuses = {item.status for item in items}
        if statuses <= {"blocked"}:
            return "blocked"
        if "blocked" in statuses:
            return "blocked"
        if "invalid" in statuses:
            return "invalid"
        if "degraded" in statuses:
            return "degraded"
        if "needs_approval" in statuses:
            return "needs_approval"
        return "simulated"

    def _summary(self, status: str, items: list[ToolDryRunResultItem]) -> str:
        count = len(items)
        if status == "blocked":
            return f"Dry-run blocked for {count} tool call(s); not executed and no real side effects occurred."
        if status == "needs_approval":
            return f"Dry-run simulated {count} tool call(s) and would require approval for side effects; not executed."
        if status == "simulated":
            return f"Dry-run simulated {count} tool call(s); not executed and no real side effects occurred."
        return f"Dry-run completed with status {status}; not executed and no real side effects occurred."

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "tool_dry_run_executor", "real_execution_enabled": False, "adapters": sorted(self.adapters)}
