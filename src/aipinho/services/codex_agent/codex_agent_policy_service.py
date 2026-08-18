from __future__ import annotations

from typing import Any

from aipinho.services.policy_kernel.workspace_role_contract_service import WorkspaceRoleContractService


class CodexAgentPolicyService:
    WRITE_CAPABILITIES = {"create_patch_preview", "apply_approved_patch", "workspace_write"}
    SHELL_CAPABILITIES = {"shell", "run_approved_shell"}

    def evaluate(self, *, config: Any, workspace_path: str | None, requested_capabilities: list[str]) -> dict[str, Any]:
        requested = set(requested_capabilities or ["codex_chat"])
        decision = {"allowed": True, "reasons": [], "requires_approval": False, "workspace": None, "blocked_capabilities": []}
        read_capabilities = {"read_workspace", "scan_workspace"}
        if requested & read_capabilities and not config.allow_read:
            decision["allowed"] = False
            decision["reasons"].append("codex_read_disabled")
            decision["blocked_capabilities"].extend(sorted(requested & read_capabilities))
        if requested & self.WRITE_CAPABILITIES and not config.allow_write:
            decision["allowed"] = False
            decision["reasons"].append("codex_write_disabled")
            decision["blocked_capabilities"].extend(sorted(requested & self.WRITE_CAPABILITIES))
        if requested & self.SHELL_CAPABILITIES and not config.allow_shell:
            decision["allowed"] = False
            decision["reasons"].append("codex_shell_disabled")
            decision["blocked_capabilities"].extend(sorted(requested & self.SHELL_CAPABILITIES))
        if requested & (self.WRITE_CAPABILITIES | self.SHELL_CAPABILITIES):
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
                    operation = self._operation_for(capability)
                    if operation is None:
                        continue
                    allowed, reason = WorkspaceRoleContractService().load().operation_allowed(contract, operation)
                    if not allowed:
                        decision["allowed"] = False
                        decision["reasons"].append(reason)
                        decision["blocked_capabilities"].append(capability)
        decision["blocked_capabilities"] = sorted(set(decision["blocked_capabilities"]))
        return decision

    def _operation_for(self, capability: str) -> str | None:
        return {
            "read_workspace": "read_workspace",
            "scan_workspace": "inspect_files",
            "create_patch_preview": "apply_patch",
            "apply_approved_patch": "apply_patch",
            "workspace_write": "create_file",
            "shell": "run_shell_test",
            "run_approved_shell": "run_shell_test",
        }.get(capability)
