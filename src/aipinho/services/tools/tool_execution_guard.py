from __future__ import annotations

from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.policy.policy_decision import PolicyResolveRequest
from aipinho.schemas.security.sandbox_decision import SandboxDecision
from aipinho.schemas.tools.tool_definition import ToolDefinition
from aipinho.schemas.tools.tool_execution import ToolExecutionRequest
from aipinho.services.governance.policy.effective_policy_decision_service import EffectivePolicyDecisionService
from aipinho.services.security.path_guard_service import PathGuardService
from aipinho.services.security.sandbox_policy_service import SandboxPolicyService
from aipinho.services.tools.tool_registry_service import ToolRegistryService
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


class ToolExecutionGuard:
    def __init__(
        self,
        registry: ToolRegistryService | None = None,
        sandbox_policy: SandboxPolicyService | None = None,
        path_guard: PathGuardService | None = None,
        policy_decisions: EffectivePolicyDecisionService | None = None,
    ) -> None:
        self.registry = registry or ToolRegistryService().load()
        self.sandbox_policy = sandbox_policy or SandboxPolicyService()
        self.path_guard = path_guard or PathGuardService()
        self.policy_decisions = policy_decisions or EffectivePolicyDecisionService()
        policy_path = PATHS.config_root / "policies" / "read_only_execution_policy.yaml"
        self.readonly_policy = load_yaml_file(policy_path, critical=True, root=policy_path.parent)

    def check(self, request: ToolExecutionRequest) -> tuple[SandboxDecision, ToolDefinition | None, dict[str, Any]]:
        violations: list[str] = []
        warnings: list[str] = []
        trace: list[dict[str, Any]] = []
        tool = self.registry.get_tool(request.tool_id)
        if tool is None:
            return self._blocked("unknown_tool", request, None, violations=["unknown_tool"]), None, {}

        allowed_actions = set(self.readonly_policy.get("read_only_execution", {}).get("allowed_actions", []) or [])
        blocked_actions = set(self.readonly_policy.get("read_only_execution", {}).get("blocked_actions", []) or [])
        workspace = request.input.get("workspace")
        path = request.input.get("path")

        if request.mode != "readonly":
            violations.append("mode_not_readonly")
        if not tool.enabled:
            violations.append("disabled_tool")
        if not tool.execute_supported:
            violations.append(self._execution_disabled_reason(tool))
        if tool.side_effect:
            violations.append("side_effect_not_allowed")
        if tool.requires_approval:
            warnings.append("approval_does_not_enable_execution_this_sprint")
        if tool.action in blocked_actions:
            violations.append(self._blocked_action_reason(tool.action))
        if tool.action not in allowed_actions:
            violations.append("action_not_allowed_for_readonly_execution")
        if tool.capability != "read_workspace":
            violations.append("capability_not_granted_for_readonly_execution")
        if not self.sandbox_policy.allows_workspace_bound_read():
            violations.append("sandbox_readonly_disabled")

        path_decision = self.path_guard.validate_read_target(str(workspace) if workspace is not None else None, str(path) if path is not None else None)
        trace.extend(path_decision.trace)
        warnings.extend(path_decision.warnings)
        if not path_decision.allowed:
            violations.extend(path_decision.violations)

        policy_decision = {}
        if tool.action in allowed_actions and tool.capability == "read_workspace" and workspace:
            try:
                policy_decision_model, _canonical = self.policy_decisions.resolve_policy_request(self._policy_request(tool, str(workspace)))
                policy_decision = _dump_model(policy_decision_model)
                trace.extend(policy_decision.get("trace", []) or [])
                if policy_decision.get("status") == "denied":
                    violations.append("policy_denied")
                if tool.capability not in set(policy_decision.get("granted_capabilities", []) or []):
                    violations.append("capability_not_granted")
            except Exception as exc:
                violations.append("policy_decision_error")
                warnings.append(str(exc))

        unique_violations = list(dict.fromkeys(violations))
        unique_warnings = list(dict.fromkeys(warnings))
        if unique_violations:
            return SandboxDecision(status="blocked", allowed=False, reason=unique_violations[0], workspace=path_decision.workspace, target_path=path_decision.target_path, normalized_workspace=path_decision.normalized_workspace, normalized_target_path=path_decision.normalized_target_path, violations=unique_violations, warnings=unique_warnings, trace=trace), tool, {"policy_decision": policy_decision}
        return SandboxDecision(status="allowed", allowed=True, reason="readonly_execution_allowed", workspace=path_decision.workspace, target_path=path_decision.target_path, normalized_workspace=path_decision.normalized_workspace, normalized_target_path=path_decision.normalized_target_path, warnings=unique_warnings, trace=trace), tool, {"policy_decision": policy_decision}

    def _policy_request(self, tool: ToolDefinition, workspace: str) -> PolicyResolveRequest:
        return PolicyResolveRequest(
            intent={"intent_type": "readonly_analysis", "requires_task": True, "requires_workspace": True, "risk_level": tool.risk_level, "confidence": 1.0, "evidence": []},
            task={"task_type": "readonly_analysis", "requested_actions": [tool.action], "read_only": True, "approval_requested": False},
            workspace={"path": workspace, "declared": True},
            role={"role_id": "executor"},
            user_constraints={"read_only": True, "no_write": True, "no_shell": True, "no_network": True},
        )

    def _execution_disabled_reason(self, tool: ToolDefinition) -> str:
        if tool.action == "apply_patch":
            return "patch_apply_disabled"
        if tool.capability == "shell" or tool.action == "run_command":
            return "shell_execution_disabled"
        if tool.action in {"git_commit", "git_push"}:
            return "git_write_disabled"
        if tool.action in {"write_files", "delete_files", "move_files"}:
            return "write_execution_disabled_this_sprint"
        return "execute_not_supported"

    def _blocked_action_reason(self, action: str) -> str:
        mapping = {"write_files": "write_execution_disabled_this_sprint", "apply_patch": "patch_apply_disabled", "run_command": "shell_execution_disabled", "git_commit": "git_write_disabled", "git_push": "git_write_disabled", "write_memory": "memory_write_disabled", "network_request": "network_disabled"}
        return mapping.get(action, "blocked_action")

    def _blocked(self, reason: str, request: ToolExecutionRequest, tool: ToolDefinition | None, *, violations: list[str]) -> SandboxDecision:
        return SandboxDecision(status="blocked", allowed=False, reason=reason, workspace=str(request.input.get("workspace") or "") or None, target_path=str(request.input.get("path") or "") or None, violations=violations)

    def status(self) -> dict[str, object]:
        return {"status": "ok", "service": "tool_execution_guard", "read_only_allowed_actions": self.readonly_policy.get("read_only_execution", {}).get("allowed_actions", [])}
