from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.agents.policy_kernel import AutoApprovalDecision, BlockReasonDefinition, PolicyKernelStatus, SafeAction
from aipinho.schemas.agents.tool_gateway import PolicyDecision, ToolDefinition, WorkspaceResolution
from aipinho.services.agents.multi_agent_policy_audit_store import MultiAgentPolicyAuditStore
from aipinho.services.events.event_core import redact_payload
from aipinho.utils.yaml_loader import load_yaml_file


CRITICAL_SHELL_CATEGORIES = {"destructive_shell", "process_control_shell", "unknown_shell"}
EXTERNAL_OR_GIT_SHELL_CATEGORIES = {"network_shell", "git_write_shell"}
SAFE_SHELL_CATEGORIES = {"readonly_shell", "test_shell", "build_shell", "package_shell", "git_read_shell"}
WRITE_CAPABILITIES = {"workspace_write", "create_file", "modify_file", "create_directory", "patch_apply"}
READ_CAPABILITIES = {"read_workspace", "search_workspace"}
ARTIFACT_CAPABILITIES = {"artifact_create", "artifact_upload", "artifact_download"}
SANDBOX_CAPABILITIES = {"sandbox_file_read", "sandbox_file_write", "sandbox_shell", "sandbox_artifact_export", "sandbox_validation", "sandbox_cleanup"}
LOW_AUTO_CAPABILITIES = {"validation", "report_generate", "patch_preview", *READ_CAPABILITIES, *ARTIFACT_CAPABILITIES, *SANDBOX_CAPABILITIES}
SECRET_PATTERN = re.compile(r"(Bearer\s+[A-Za-z0-9._~+/-]+|sk-[A-Za-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{20,}|token=|api_key=)", re.IGNORECASE)


class MultiAgentPolicyKernelService:
    def __init__(
        self,
        *,
        profile_path: Path | None = None,
        autoapproval_path: Path | None = None,
        block_reasons_path: Path | None = None,
        root: Path | None = None,
        store: MultiAgentPolicyAuditStore | None = None,
    ) -> None:
        self.root = root or PATHS.config_root
        self.profile_path = profile_path or self.root / "agents" / "agent_policy_profiles.yaml"
        self.autoapproval_path = autoapproval_path or self.root / "policies" / "multi_agent_autoapproval_policy.yaml"
        self.block_reasons_path = block_reasons_path or self.root / "policies" / "block_reason_codes.yaml"
        self.store = store or MultiAgentPolicyAuditStore()

    def status(self) -> PolicyKernelStatus:
        profiles = self._profiles()
        reasons = self._block_reasons()
        policy = self._policy()
        return PolicyKernelStatus(
            status="ok",
            profiles_loaded=len(profiles),
            block_reason_codes_loaded=len(reasons),
            default_execution_mode=str(policy.get("default_execution_mode", "governed_autorun")),
            power_user_enabled=bool(policy.get("enable_power_user_mode", True)),
            unrestricted_local_lab_enabled=bool(policy.get("enable_unrestricted_local_lab", False)),
        )

    def evaluate_tool_invocation(
        self,
        *,
        agent_id: str,
        session_id: str,
        run_id: str,
        tool: ToolDefinition,
        workspace: WorkspaceResolution | None,
        input_summary_sanitized: str,
        shell_category: str | None = None,
        tool_invocation_id: str | None = None,
        operation_type: str | None = None,
        execution_mode: str | None = None,
    ) -> PolicyDecision:
        profile = self._profile(agent_id)
        mode = self._execution_mode(profile, execution_mode)
        capability = tool.capability
        workspace_role = workspace.workspace_role if workspace is not None else "unknown"
        risk = self._classify_risk(tool=tool, capability=capability, workspace_role=workspace_role, shell_category=shell_category)

        if self._contains_secret_risk(input_summary_sanitized):
            return self._decision("deny", "secret_access_blocked", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)
        if not tool.enabled:
            return self._decision("deny", "tool_disabled", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)
        if agent_id in tool.agent_denylist or (tool.agent_allowlist and agent_id not in tool.agent_allowlist):
            return self._decision("deny", "agent_not_allowed", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)
        if not profile.get("can_use_tool_gateway", True):
            return self._decision("deny", "capability_not_allowed", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)
        if mode == "unrestricted_local_lab" and not self._policy().get("enable_unrestricted_local_lab", False):
            return self._decision("deny", "policy_unclassified", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)

        if tool.requires_workspace:
            workspace_decision = self._workspace_decision(tool, workspace, risk, mode, agent_id, session_id, run_id, tool_invocation_id, operation_type)
            if workspace_decision is not None:
                return workspace_decision

        if tool.can_run_shell:
            if capability == "sandbox_shell":
                return self._decision("auto_approve", "sandbox_shell_allowed", agent_id, session_id, run_id, tool, workspace, "medium", mode, tool_invocation_id, operation_type)
            shell_decision = self._shell_decision(shell_category or "unknown_shell", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)
            if shell_decision is not None:
                return shell_decision

        if capability in SANDBOX_CAPABILITIES:
            reason = {
                "sandbox_artifact_export": "sandbox_artifact_export_allowed",
                "sandbox_validation": "sandbox_validation_allowed",
                "sandbox_cleanup": "sandbox_cleanup_preview_allowed",
            }.get(capability, "sandbox_allowed_low_risk")
            return self._decision("auto_approve", reason, agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)

        if mode == "safe_chat" and (tool.can_modify_filesystem or tool.can_run_shell or capability in WRITE_CAPABILITIES):
            return self._decision("deny", "capability_not_allowed", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)

        if risk == "critical":
            return self._decision("deny", "risk_too_high", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)
        if risk == "high":
            return self._decision("require_approval", "approval_required", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)

        if self._auto_allowed(mode, capability, workspace_role, risk):
            return self._decision("auto_approve", f"{capability}_auto_approved", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)
        if self._approval_required(mode, capability):
            return self._decision("require_approval", "approval_required", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)
        return self._decision("allow", "policy_allowed", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)

    def _workspace_decision(
        self,
        tool: ToolDefinition,
        workspace: WorkspaceResolution | None,
        risk: str,
        mode: str,
        agent_id: str,
        session_id: str,
        run_id: str,
        tool_invocation_id: str | None,
        operation_type: str | None,
    ) -> PolicyDecision | None:
        if workspace is None:
            return self._decision("deny", "workspace_unknown", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)
        if not workspace.allowed:
            reason = self._normalize_workspace_reason(workspace.reason_code)
            return self._decision("deny", reason, agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)
        if workspace.workspace_role == "source_readonly" and (tool.can_modify_filesystem or tool.capability in WRITE_CAPABILITIES):
            return self._decision("deny", "source_readonly_write_denied", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)
        if workspace.workspace_role in {"forbidden", "protected"}:
            reason = "workspace_forbidden" if workspace.workspace_role == "forbidden" else "workspace_protected"
            return self._decision("deny", reason, agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)
        if workspace.workspace_role == "system_mutable" and (tool.can_modify_filesystem or tool.capability in WRITE_CAPABILITIES):
            if not self._policy().get("autoapprove_system_write", False) and not self._system_mutable_write_allowed_by_policy(
                mode=mode,
                capability=tool.capability,
                operation_type=operation_type or tool.tool_name,
            ):
                return self._decision("require_approval", "approval_required", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)
        return None

    def _shell_decision(
        self,
        shell_category: str,
        agent_id: str,
        session_id: str,
        run_id: str,
        tool: ToolDefinition,
        workspace: WorkspaceResolution | None,
        risk: str,
        mode: str,
        tool_invocation_id: str | None,
        operation_type: str | None,
    ) -> PolicyDecision | None:
        if shell_category in CRITICAL_SHELL_CATEGORIES:
            reason = {
                "destructive_shell": "destructive_shell_blocked",
                "process_control_shell": "process_control_blocked",
                "unknown_shell": "unknown_shell_blocked",
            }.get(shell_category, "risk_too_high")
            return self._decision("deny", reason, agent_id, session_id, run_id, tool, workspace, "critical", mode, tool_invocation_id, operation_type)
        if shell_category in EXTERNAL_OR_GIT_SHELL_CATEGORIES:
            if mode == "power_user":
                return self._decision("require_approval", "approval_required", agent_id, session_id, run_id, tool, workspace, "high", mode, tool_invocation_id, operation_type)
            reason = "network_shell_blocked" if shell_category == "network_shell" else "git_write_blocked"
            return self._decision("deny", reason, agent_id, session_id, run_id, tool, workspace, "high", mode, tool_invocation_id, operation_type)
        if shell_category in SAFE_SHELL_CATEGORIES:
            if self._auto_allowed(mode, shell_category, workspace.workspace_role if workspace else "unknown", risk):
                return self._decision("auto_approve", f"{shell_category}_auto_approved", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)
            return self._decision("require_approval", "approval_required", agent_id, session_id, run_id, tool, workspace, risk, mode, tool_invocation_id, operation_type)
        return self._decision("deny", "unknown_shell_blocked", agent_id, session_id, run_id, tool, workspace, "critical", mode, tool_invocation_id, operation_type)

    def _decision(
        self,
        decision: str,
        reason_code: str,
        agent_id: str,
        session_id: str,
        run_id: str,
        tool: ToolDefinition,
        workspace: WorkspaceResolution | None,
        risk_level: str,
        execution_mode: str,
        tool_invocation_id: str | None,
        operation_type: str | None,
    ) -> PolicyDecision:
        reason = self._block_reason(reason_code)
        safe_actions = []
        auto_approval_id = None
        approval_required = decision == "require_approval"
        if decision == "auto_approve":
            auto = AutoApprovalDecision(
                policy_decision_id="pending",
                agent_id=agent_id,
                session_id=session_id,
                run_id=run_id,
                tool_invocation_id=tool_invocation_id,
                action_type=operation_type or tool.tool_name,
                capability=tool.capability,
                workspace_id=workspace.workspace_id if workspace else None,
                workspace_role=workspace.workspace_role if workspace else None,
                risk_level=risk_level,
                execution_mode=execution_mode,
                approved=True,
                reason_code=reason_code,
                human_reason=reason.human_reason,
                technical_reason_sanitized=reason_code,
                evidence_refs=[f"policy:{reason_code}"],
            )
            auto_approval_id = auto.auto_approval_id
        if approval_required:
            safe_action = SafeAction(
                label="Aprovar acao governada",
                kind="approve",
                agent_id=agent_id,
                session_id=session_id,
                run_id=run_id,
                tool_invocation_id=tool_invocation_id,
                approval_id=f"approval_{tool_invocation_id or 'pending'}",
                endpoint_ref=f"/api/v1/tools/invocations/{tool_invocation_id}/approve" if tool_invocation_id else None,
                method="POST",
                side_effect=self._side_effect(tool),
                human_explanation=reason.human_reason,
                risk_level=risk_level,
            )
            safe_actions.append(safe_action.model_dump())
        policy = PolicyDecision(
            agent_id=agent_id,
            session_id=session_id,
            run_id=run_id,
            tool_invocation_id=tool_invocation_id,
            operation_type=operation_type or tool.tool_name,
            capability=tool.capability,
            workspace_id=workspace.workspace_id if workspace else None,
            workspace_role=workspace.workspace_role if workspace else None,
            risk_level=risk_level,
            execution_mode=execution_mode,
            decision=decision,  # type: ignore[arg-type]
            reason_code=reason_code,
            human_reason=reason.human_reason,
            technical_reason_sanitized=redact_payload(reason_code),
            approval_required=approval_required,
            auto_approval_id=auto_approval_id,
            safe_alternative=reason.safe_alternative,
            safe_actions=safe_actions,
            evidence_refs=[f"policy:{reason_code}", *(workspace.evidence_refs if workspace else [])],
        )
        self.store.save_policy_decision(policy)
        if decision == "auto_approve" and auto_approval_id:
            auto = AutoApprovalDecision(
                auto_approval_id=auto_approval_id,
                policy_decision_id=policy.policy_decision_id,
                agent_id=agent_id,
                session_id=session_id,
                run_id=run_id,
                tool_invocation_id=tool_invocation_id,
                action_type=operation_type or tool.tool_name,
                capability=tool.capability,
                workspace_id=policy.workspace_id,
                workspace_role=policy.workspace_role,
                risk_level=risk_level,
                execution_mode=execution_mode,
                approved=True,
                reason_code=reason_code,
                human_reason=reason.human_reason,
                technical_reason_sanitized=reason_code,
                evidence_refs=policy.evidence_refs,
            )
            self.store.save_auto_approval(auto)
        return policy

    def _auto_allowed(self, mode: str, capability: str, workspace_role: str, risk: str) -> bool:
        policy = self._policy()
        matrix = policy.get("autoapproval_matrix", {})
        mode_policy = matrix.get(mode, {}) if isinstance(matrix, dict) else {}
        if mode == "safe_chat":
            return bool(mode_policy.get(capability, False)) or capability in {"artifact_create", "artifact_upload", "artifact_download", "validation", "report_generate"}
        if risk == "low" and bool(policy.get("autoapprove_low_risk", True)):
            return True
        if risk == "medium" and bool(policy.get("autoapprove_medium_risk", True)) and mode in {"governed_autorun", "power_user", "unrestricted_local_lab"}:
            if capability in WRITE_CAPABILITIES and workspace_role not in {"target_mutable"}:
                return False
            return True
        if capability in mode_policy:
            return bool(mode_policy.get(capability))
        return capability in LOW_AUTO_CAPABILITIES and mode in {"assisted_execution", "governed_autorun", "power_user", "unrestricted_local_lab"}

    def _approval_required(self, mode: str, capability: str) -> bool:
        return mode in {"assisted_execution", "power_user", "unrestricted_local_lab"} and capability in WRITE_CAPABILITIES | {"shell"}

    def _system_mutable_write_allowed_by_policy(self, *, mode: str, capability: str, operation_type: str) -> bool:
        policy = self._policy().get("system_mutable_write_policy", {})
        if not isinstance(policy, dict):
            return False
        modes = {str(item) for item in policy.get("modes", [])}
        operations = {str(item) for item in policy.get("allow_operations", [])}
        capabilities = {str(item) for item in policy.get("allowed_capabilities", [])}
        if modes and mode not in modes:
            return False
        if capabilities and capability not in capabilities:
            return False
        return operation_type in operations

    def _classify_risk(self, *, tool: ToolDefinition, capability: str, workspace_role: str, shell_category: str | None) -> str:
        if shell_category in CRITICAL_SHELL_CATEGORIES:
            return "critical"
        if shell_category in EXTERNAL_OR_GIT_SHELL_CATEGORIES:
            return "high"
        if tool.can_run_shell:
            return "medium" if shell_category in SAFE_SHELL_CATEGORIES else "high"
        if capability == "patch_apply" or tool.requires_approval:
            return "medium" if workspace_role == "target_mutable" else "high"
        if tool.can_modify_filesystem:
            return "medium"
        return tool.risk_level or "low"

    def _contains_secret_risk(self, value: str) -> bool:
        return bool(SECRET_PATTERN.search(value))

    def _normalize_workspace_reason(self, reason_code: str) -> str:
        return {
            "workspace_deny_override": "workspace_forbidden",
            "path_traversal_or_outside_workspace": "path_traversal_denied",
            "source_readonly_write_denied": "source_readonly_write_denied",
        }.get(reason_code, reason_code or "workspace_unknown")

    def _side_effect(self, tool: ToolDefinition) -> str:
        if tool.can_run_shell:
            return "shell"
        if tool.can_modify_filesystem:
            return "filesystem_write"
        if tool.produces_artifacts:
            return "artifact"
        return "none"

    def _execution_mode(self, profile: dict[str, Any], requested: str | None) -> str:
        if requested:
            return requested
        return str(profile.get("default_mode") or self._policy().get("default_execution_mode", "governed_autorun"))

    def _profile(self, agent_id: str) -> dict[str, Any]:
        return self._profiles().get(agent_id) or {
            "agent_id": agent_id,
            "role": "unknown",
            "default_mode": self._policy().get("default_execution_mode", "governed_autorun"),
            "can_use_tool_gateway": True,
        }

    def _profiles(self) -> dict[str, dict[str, Any]]:
        data = load_yaml_file(self.profile_path, critical=False, root=self.root)
        profiles = data.get("agent_policy_profiles", [])
        if not isinstance(profiles, list):
            return {}
        return {str(item.get("agent_id")): item for item in profiles if isinstance(item, dict) and item.get("agent_id")}

    def _policy(self) -> dict[str, Any]:
        data = load_yaml_file(self.autoapproval_path, critical=False, root=self.root)
        if not data:
            return {
                "default_execution_mode": "governed_autorun",
                "enable_power_user_mode": True,
                "enable_unrestricted_local_lab": False,
                "autoapprove_low_risk": True,
                "autoapprove_medium_risk": True,
            }
        return data

    def _block_reasons(self) -> dict[str, BlockReasonDefinition]:
        data = load_yaml_file(self.block_reasons_path, critical=False, root=self.root)
        modern = data.get("block_reason_codes", [])
        legacy = data.get("codes", [])
        items: list[dict[str, Any]] = []
        if isinstance(modern, list):
            items.extend(item for item in modern if isinstance(item, dict))
        if isinstance(legacy, list):
            for item in legacy:
                if not isinstance(item, dict):
                    continue
                code = item.get("reason_code") or item.get("code")
                if not code:
                    continue
                items.append({
                    "reason_code": code,
                    "human_reason": item.get("human_reason") or item.get("mobile_normal_message") or item.get("human_reason_template") or f"Acao bloqueada: {code}.",
                    "safe_alternative": self._legacy_safe_alternative(item),
                    "severity": item.get("severity", "warning"),
                })
        reasons: dict[str, BlockReasonDefinition] = {}
        for item in items:
            reason_code = str(item.get("reason_code") or item.get("code") or "")
            if not reason_code:
                continue
            reasons[reason_code] = BlockReasonDefinition(
                reason_code=reason_code,
                human_reason=str(item.get("human_reason") or f"Acao bloqueada: {reason_code}."),
                safe_alternative=item.get("safe_alternative"),
                severity=str(item.get("severity", "warning")),
            )
        return reasons

    def _legacy_safe_alternative(self, item: dict[str, Any]) -> str | None:
        alt = item.get("safe_alternative")
        if alt:
            return str(alt)
        alternatives = item.get("safe_alternatives")
        if isinstance(alternatives, list) and alternatives:
            return str(alternatives[0])
        return None

    def _block_reason(self, code: str) -> BlockReasonDefinition:
        reasons = self._block_reasons()
        if code in reasons:
            return reasons[code]
        if code.endswith("_auto_approved") or code == "policy_allowed":
            return BlockReasonDefinition(reason_code=code, human_reason="Acao permitida pela politica governada.", safe_alternative=None, severity="info")
        if code == "approval_required":
            return BlockReasonDefinition(reason_code=code, human_reason="A acao precisa de aprovacao humana antes de continuar.", safe_alternative="Revise os detalhes e aprove somente se concordar com o efeito.", severity="warning")
        return BlockReasonDefinition(reason_code=code, human_reason="Acao bloqueada pela politica.", safe_alternative="Revise o pedido, reduza o risco ou escolha um workspace permitido.", severity="warning")
