from __future__ import annotations

from typing import Any

from aipinho.services.gemini_executor.gemini_executor_config_service import GeminiExecutorRuntimeConfig
from aipinho.services.policy_kernel.workspace_role_contract_service import WorkspaceRoleContractService


class GeminiExecutorPolicyService:
    WRITE_CAPABILITIES = {"create_patch_preview", "apply_approved_patch", "create_file", "modify_file"}
    SHELL_CAPABILITIES = {"run_approved_shell", "run_shell_readonly", "run_shell_test", "run_shell_build"}

    def evaluate(self, *, config: GeminiExecutorRuntimeConfig, workspace_path: str | None, requested_capabilities: list[str]) -> dict[str, Any]:
        requested = set(requested_capabilities)
        decision: dict[str, Any] = {
            "allowed": True,
            "reasons": [],
            "requires_approval": False,
            "workspace": None,
            "blocked_capabilities": [],
        }
        if not config.enabled:
            return {**decision, "allowed": False, "reasons": ["gemini_executor_disabled"]}
        if len(requested) == 0:
            requested.add("gemini_chat")
        if requested & self.WRITE_CAPABILITIES and not config.allow_write:
            decision["allowed"] = False
            decision["reasons"].append("gemini_write_disabled")
            decision["blocked_capabilities"].extend(sorted(requested & self.WRITE_CAPABILITIES))
        if requested & self.SHELL_CAPABILITIES and not config.allow_shell:
            decision["allowed"] = False
            decision["reasons"].append("gemini_shell_disabled")
            decision["blocked_capabilities"].extend(sorted(requested & self.SHELL_CAPABILITIES))
        if config.require_approval_for_write and requested & self.WRITE_CAPABILITIES:
            decision["requires_approval"] = True
        if config.require_approval_for_shell and requested & self.SHELL_CAPABILITIES:
            decision["requires_approval"] = True
        if workspace_path:
            workspace_decision = WorkspaceRoleContractService().load().resolve(workspace_path, required=False)
            decision["workspace"] = workspace_decision.model_dump()
            contract = workspace_decision.contract
            if workspace_decision.status != "allowed" or contract is None:
                decision["allowed"] = False
                decision["reasons"].append(workspace_decision.reason)
            else:
                for capability in sorted(requested):
                    operation = self._capability_to_operation(capability)
                    if operation is None:
                        continue
                    allowed, reason = WorkspaceRoleContractService().load().operation_allowed(contract, operation)
                    if not allowed:
                        decision["allowed"] = False
                        decision["reasons"].append(reason)
                        decision["blocked_capabilities"].append(capability)
        return decision

    def _capability_to_operation(self, capability: str) -> str | None:
        return {
            "read_workspace": "read_workspace",
            "scan_workspace": "inspect_files",
            "create_patch_preview": "apply_patch",
            "apply_approved_patch": "apply_patch",
            "run_approved_shell": "run_shell_test",
            "run_shell_readonly": "run_shell_readonly",
            "run_shell_test": "run_shell_test",
            "run_shell_build": "run_shell_build",
        }.get(capability)

