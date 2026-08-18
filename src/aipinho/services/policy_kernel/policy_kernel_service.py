from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.policy.policy_decision import PolicyDecision, PolicyResolveRequest
from aipinho.schemas.tasks.task_contract import ContractType, TaskContractPreview
from aipinho.services.policy_kernel.action_registry_service import ActionRegistryService
from aipinho.services.policy_kernel.approval_policy_service import ApprovalPolicyService
from aipinho.services.policy_kernel.capability_gate_service import CapabilityGateService, CapabilityRegistryService
from aipinho.services.policy_kernel.effective_policy_builder import EffectivePolicyBuilder
from aipinho.services.policy_kernel.policy_context_builder import PolicyContextBuilder
from aipinho.services.policy_kernel.policy_trace_service import PolicyTraceService
from aipinho.services.policy_kernel.workspace_policy_service import WorkspacePolicyService


class PolicyKernelService:
    CONTRACT_TYPES: set[str] = {
        "conversation",
        "readonly_analysis",
        "artifact_generation",
        "filesystem_write",
        "file_modification",
        "project_generation",
        "artifact_build",
        "shell_execution",
        "web_search",
        "project_build",
        "patch_request",
        "patch_apply",
        "validation",
        "validation_request",
        "in_chat_final_report",
        "memory_curation",
        "unknown",
    }

    def __init__(
        self,
        action_registry: ActionRegistryService | None = None,
        capability_registry: CapabilityRegistryService | None = None,
        approval_policy: ApprovalPolicyService | None = None,
        trace_service: PolicyTraceService | None = None,
    ) -> None:
        self.trace_service = trace_service or PolicyTraceService()
        self.action_registry = action_registry or ActionRegistryService().load()
        self.capability_registry = capability_registry or CapabilityRegistryService().load()
        self.approval_policy = approval_policy or ApprovalPolicyService(action_registry=self.action_registry).load()
        self.context_builder = PolicyContextBuilder(action_registry=self.action_registry, trace_service=self.trace_service)
        self.workspace_policy = WorkspacePolicyService(trace_service=self.trace_service).load()
        self.capability_gate = CapabilityGateService(
            registry=self.capability_registry,
            action_registry=self.action_registry,
            trace_service=self.trace_service,
        )
        self.effective_policy_builder = EffectivePolicyBuilder(
            action_registry=self.action_registry,
            approval_policy=self.approval_policy,
            trace_service=self.trace_service,
        )

    def _contract_type(self, request: PolicyResolveRequest) -> ContractType:
        if request.task.task_type != "unknown":
            return request.task.task_type
        intent_type = request.intent.intent_type
        if intent_type == "memory_write":
            return "memory_curation"
        if intent_type in self.CONTRACT_TYPES:
            return intent_type  # type: ignore[return-value]
        return "unknown"

    def _safe_to_execute(
        self,
        decision_status: str,
        requested_actions: list[str],
        allowed_actions: list[str],
        approval_required_for: list[str],
    ) -> bool:
        if decision_status != "allowed" or not requested_actions:
            return False
        if set(requested_actions) != set(allowed_actions):
            return False
        if approval_required_for:
            return False
        for action in requested_actions:
            if self.approval_policy.never_auto_execute(action):
                return False
        return True

    def resolve(self, request: PolicyResolveRequest) -> PolicyDecision:
        context = self.context_builder.build(request)
        contract_type = self._contract_type(request)
        workspace = self.workspace_policy.evaluate(
            workspace_path=request.workspace.path,
            requires_workspace=request.intent.requires_workspace,
        )
        capability_result = self.capability_gate.evaluate(
            actions=context.normalized_actions,
            read_only=request.task.read_only or request.user_constraints.read_only,
            no_write=request.user_constraints.no_write,
            no_shell=request.user_constraints.no_shell,
            no_network=request.user_constraints.no_network,
            workspace_blocked=workspace.blocked,
        )
        effective = self.effective_policy_builder.build(
            context=context,
            workspace=workspace,
            capabilities=capability_result,
        )
        trace = [
            *context.trace,
            *workspace.trace,
            *capability_result.trace,
            *effective.trace,
        ]
        violations = list(effective.violations)
        warnings = list(effective.warnings)
        requested_denied = any(action in effective.policy.denied_actions for action in context.normalized_actions)

        if workspace.needs_clarification:
            status = "needs_clarification"
        elif workspace.blocked or context.unknown_actions or requested_denied:
            status = "denied"
        elif effective.policy.approval_required_for:
            status = "needs_approval"
        else:
            status = "allowed"

        safe_to_preview = status in {"allowed", "needs_approval"}
        safe_to_execute = self._safe_to_execute(
            status,
            context.normalized_actions,
            effective.policy.allowed_actions,
            effective.policy.approval_required_for,
        )
        trace.append(self.trace_service.create(
            stage="final_decision",
            rule="default_deny_unless_explicitly_allowed",
            decision=status,
            reason="policy_kernel_completed_restrictive_decision",
            severity="info" if status == "allowed" else "warning",
            source="services/policy_kernel/policy_kernel_service.py",
            input={"safe_to_preview": safe_to_preview, "safe_to_execute": safe_to_execute},
        ))
        return PolicyDecision(
            decision_id=f"policy_{uuid4().hex}",
            status=status,  # type: ignore[arg-type]
            contract_type=contract_type,
            allowed_actions=effective.policy.allowed_actions,
            denied_actions=effective.policy.denied_actions,
            approval_required_for=effective.policy.approval_required_for,
            granted_capabilities=effective.policy.granted_capabilities,
            denied_capabilities=effective.policy.denied_capabilities,
            effective_policy=effective.policy,
            violations=violations,
            warnings=warnings,
            trace=trace,
            safe_to_execute=safe_to_execute,
            safe_to_preview=safe_to_preview,
        )

    def explain(self, request: PolicyResolveRequest) -> dict[str, object]:
        decision = self.resolve(request)
        explanation = (
            f"Policy decision is {decision.status}. "
            f"Allowed actions: {', '.join(decision.allowed_actions) or 'none'}. "
            f"Denied actions: {', '.join(decision.denied_actions) or 'none'}. "
            f"Approval required for: {', '.join(decision.approval_required_for) or 'none'}."
        )
        return {"status": "ok", "explanation": explanation, "decision": decision}

    def contract_preview(self, request: PolicyResolveRequest) -> TaskContractPreview:
        decision = self.resolve(request)
        return TaskContractPreview(
            contract_type=decision.contract_type,
            requires_task=request.intent.requires_task,
            requires_workspace=request.intent.requires_workspace,
            requested_actions=request.task.requested_actions,
            allowed_actions=decision.allowed_actions,
            denied_actions=decision.denied_actions,
            approval_required_for=decision.approval_required_for,
            safe_to_preview=decision.safe_to_preview,
            safe_to_execute=decision.safe_to_execute,
            policy_decision_id=decision.decision_id,
        )

    def status(self) -> dict[str, object]:
        statuses = {
            "action_registry": self.action_registry.status(),
            "capability_registry": self.capability_registry.status(),
            "approval_policy": self.approval_policy.status(),
            "workspace_policy": self.workspace_policy.status(),
            "effective_policy_builder": {"status": "ok"},
            "policy_kernel": {"status": "ok"},
        }
        overall = "ok" if all(item.get("status") == "ok" for item in statuses.values()) else "degraded"
        return {"status": overall, **statuses}
