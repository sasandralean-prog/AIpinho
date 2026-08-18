from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.policy.policy_decision import PolicyResolveRequest
from aipinho.schemas.tools.tool_call import ToolCall
from aipinho.schemas.tools.tool_definition import ToolDefinition
from aipinho.schemas.tools.tool_safety import ToolSafetyDecision
from aipinho.services.approvals.approval_service import ApprovalService
from aipinho.services.governance.policy.effective_policy_decision_service import EffectivePolicyDecisionService
from aipinho.services.security.path_guard_service import PathGuardService
from aipinho.services.tools.tool_input_validator import ToolInputValidator
from aipinho.services.tools.tool_registry_service import ToolRegistryService
from aipinho.services.tools.tool_trace_service import ToolTraceService
from aipinho.utils.yaml_loader import load_yaml_file


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


class ToolSafetyService:
    def __init__(
        self,
        registry: ToolRegistryService | None = None,
        validator: ToolInputValidator | None = None,
        policy_decisions: EffectivePolicyDecisionService | None = None,
        approval_service: ApprovalService | None = None,
        path_guard: PathGuardService | None = None,
        trace: ToolTraceService | None = None,
    ) -> None:
        self.registry = registry or ToolRegistryService().load()
        self.validator = validator or ToolInputValidator()
        self.policy_decisions = policy_decisions or EffectivePolicyDecisionService()
        self.approval_service = approval_service or ApprovalService()
        self.path_guard = path_guard or PathGuardService()
        self.trace = trace or ToolTraceService()
        policy_path = PATHS.config_root / "policies" / "governed_tool_execution_policy.yaml"
        self.governed_policy = load_yaml_file(policy_path, critical=False, root=policy_path.parent)

    def check(self, call: ToolCall) -> tuple[ToolSafetyDecision, ToolDefinition | None, dict[str, Any]]:
        trace = []
        warnings: list[str] = []
        blocked: list[str] = []
        policy_decision: dict[str, Any] = {}
        approval_snapshot: dict[str, Any] = {}
        tool = self.registry.get_tool(call.tool_id)

        if tool is None:
            trace.append(self.trace.item(stage="tool_safety", rule="tool_exists", decision="blocked", reason="unknown_tool", severity="error", source="config/tools/tool_registry.yaml", data={"tool_id": call.tool_id}))
            return ToolSafetyDecision(status="blocked", blocked=True, blocked_reasons=["unknown_tool"], safe_to_execute=False, safe_to_dry_run=False, trace=trace), None, {}

        if not tool.enabled:
            blocked.append("disabled_tool")
        if call.mode == "dry_run" and not tool.dry_run_supported:
            blocked.append("dry_run_not_supported")
        if call.mode == "execute" and not tool.execute_supported:
            blocked.append("tool_execute_blocked_unsupported_mode")

        validation = self.validator.validate(tool, call)
        trace.extend(validation.trace)
        warnings.extend(validation.warnings)
        if not validation.input_valid:
            blocked.extend(validation.violations or ["invalid_input"])
        workspace = str(call.input.get("workspace") or "")
        if workspace:
            if workspace and not self._workspace_allowlisted(workspace):
                blocked.append("tool_execute_blocked_by_workspace")
            path_decision = self.path_guard.validate_read_target(
                workspace,
                str(call.input.get("path") or "."),
            )
            trace.extend(path_decision.trace)
            warnings.extend(path_decision.warnings)
            if not path_decision.allowed:
                blocked.extend(path_decision.violations)

        approval = None
        if call.approval_id:
            approval = self.approval_service.get_approval(call.approval_id)
            if approval is None:
                warnings.append("approval_not_found")
                trace.append(self.trace.item(stage="tool_safety", rule="approval_evidence", decision="warning", reason="approval_not_found", severity="warning", data={"approval_id": call.approval_id}))
            else:
                approval_snapshot = _dump_model(approval)
                trace.append(self.trace.item(stage="tool_safety", rule="approval_evidence", decision=approval.status, reason="approval_record_loaded_for_trace_only", source="data/runtime/approvals", data={"approval_id": approval.approval_id, "execution_status": approval.execution_status}))

        if blocked:
            trace.append(self.trace.item(stage="tool_safety", rule="dry_run_preconditions", decision="blocked", reason="blocked_before_policy", severity="error", source="services/tools/tool_safety_service.py", data={"blocked_reasons": blocked}))
            return ToolSafetyDecision(status="blocked", blocked=True, blocked_reasons=list(dict.fromkeys(blocked)), warnings=warnings, safe_to_execute=False, safe_to_dry_run=False, trace=trace), tool, {"approval_snapshot": approval_snapshot}

        try:
            request = self._policy_request(tool, call)
            decision, _canonical = self.policy_decisions.resolve_policy_request(request)
            policy_decision = _dump_model(decision)
        except Exception as exc:
            trace.append(self.trace.item(stage="tool_safety", rule="effective_policy_decision", decision="blocked", reason="policy_decision_error", severity="error", source="services/governance/policy/effective_policy_decision_service.py", data={"error": str(exc)}))
            return ToolSafetyDecision(status="blocked", blocked=True, blocked_reasons=["policy_decision_error"], warnings=warnings, safe_to_execute=False, safe_to_dry_run=False, trace=trace), tool, {"approval_snapshot": approval_snapshot}

        if policy_decision.get("status") == "denied":
            trace.append(self.trace.item(stage="tool_safety", rule="effective_policy_decision", decision="blocked", reason="policy_denied_tool_action", severity="error", source="EffectivePolicyDecisionService", data={"policy_status": policy_decision.get("status")}))
            return ToolSafetyDecision(status="blocked", blocked=True, blocked_reasons=["tool_execute_blocked_by_policy"], warnings=warnings, safe_to_execute=False, safe_to_dry_run=False, trace=trace), tool, {"policy_decision": policy_decision, "approval_snapshot": approval_snapshot}

        approval_required = list(dict.fromkeys([*policy_decision.get("approval_required_for", []), *([tool.action] if tool.requires_approval else [])]))
        if approval_required:
            approval_valid = bool(
                approval is not None
                and approval.status == "approved"
                and tool.action in set(approval.actions_requested)
            )
            if call.mode == "execute" and not approval_valid:
                trace.append(self.trace.item(stage="tool_safety", rule="approval_evidence", decision="needs_approval", reason="tool_execute_blocked_missing_approval", severity="warning", source="services/approvals/approval_service.py", data={"approval_required_for": approval_required}))
                return ToolSafetyDecision(status="needs_approval", blocked=False, approval_required_for=approval_required, warnings=warnings, safe_to_execute=False, safe_to_dry_run=tool.dry_run_supported, trace=trace), tool, {"policy_decision": policy_decision, "approval_snapshot": approval_snapshot}
            if call.mode == "dry_run":
                trace.append(self.trace.item(stage="tool_safety", rule="side_effect_simulation", decision="needs_approval", reason="tool_dry_run_allowed_approval_required_for_execute", severity="warning", source="config/policies/tool_dry_run_policy.yaml", data={"approval_required_for": approval_required}))
                return ToolSafetyDecision(status="needs_approval", blocked=False, approval_required_for=approval_required, warnings=warnings, safe_to_execute=False, safe_to_dry_run=True, trace=trace), tool, {"policy_decision": policy_decision, "approval_snapshot": approval_snapshot}

        if call.mode == "execute":
            trace.append(self.trace.item(stage="tool_safety", rule="governed_execute", decision="allowed", reason="tool_execute_allowed", source="services/tools/tool_safety_service.py"))
            return ToolSafetyDecision(status="allowed", blocked=False, warnings=warnings, safe_to_execute=True, safe_to_dry_run=tool.dry_run_supported, trace=trace), tool, {"policy_decision": policy_decision, "approval_snapshot": approval_snapshot}

        trace.append(self.trace.item(stage="tool_safety", rule="dry_run_allowed", decision="allowed", reason="tool_can_be_simulated_without_real_side_effects", source="config/policies/tool_dry_run_policy.yaml"))
        return ToolSafetyDecision(status="allowed", blocked=False, warnings=warnings, safe_to_execute=False, safe_to_dry_run=True, trace=trace), tool, {"policy_decision": policy_decision, "approval_snapshot": approval_snapshot}

    def _workspace_allowlisted(self, workspace: str) -> bool:
        roots = (
            self.governed_policy.get("governed_tool_execution", {}).get("allowed_workspace_roots", [])
            if isinstance(self.governed_policy, dict)
            else []
        )
        target = os.path.normcase(str(Path(workspace).resolve(strict=False)))
        for item in roots or []:
            root = os.path.normcase(str(Path(str(item)).resolve(strict=False)))
            if target == root or target.startswith(root + os.sep):
                return True
        return False

    def _policy_request(self, tool: ToolDefinition, call: ToolCall) -> PolicyResolveRequest:
        path = call.input.get("path") or call.input.get("workspace")
        has_workspace = isinstance(path, str) and bool(path.strip())
        task_type = self._task_type_for_tool(tool)
        intent_type = self._intent_type_for_tool(tool)
        read_only = not tool.side_effect and tool.capability not in {"git", "shell", "network"}
        return PolicyResolveRequest(
            intent={
                "intent_type": intent_type,
                "requires_task": True,
                "requires_workspace": has_workspace,
                "risk_level": tool.risk_level,
                "confidence": 1.0,
                "evidence": [],
            },
            task={
                "task_type": task_type,
                "requested_actions": [tool.action],
                "read_only": read_only,
                "approval_requested": bool(tool.requires_approval),
            },
            workspace={"path": path if has_workspace else None, "declared": has_workspace},
            role={"role_id": "executor"},
            user_constraints={"read_only": False, "no_write": False, "no_shell": False, "no_network": False},
        )

    def _task_type_for_tool(self, tool: ToolDefinition) -> str:
        if tool.category == "patch":
            return "patch_request"
        if tool.action == "write_files":
            return "artifact_generation"
        if tool.action == "write_memory":
            return "memory_curation"
        if tool.action == "run_command":
            return "validation"
        return "readonly_analysis"
    def _intent_type_for_tool(self, tool: ToolDefinition) -> str:
        if tool.category == "patch":
            return "patch_request"
        if tool.action == "write_files":
            return "artifact_generation"
        if tool.action == "write_memory":
            return "memory_write"
        if tool.action == "run_command":
            return "validation_request"
        return "readonly_analysis"
