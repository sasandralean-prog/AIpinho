from __future__ import annotations

from dataclasses import dataclass, field

from aipinho.core.exceptions import ConfigValidationError
from aipinho.registries.role_registry import RoleRegistry
from aipinho.schemas.policy.policy_decision import PolicyResolveRequest
from aipinho.schemas.policy.policy_trace import PolicyTraceItem
from aipinho.schemas.policy.policy_violation import PolicyViolation
from aipinho.schemas.roles.role_definition import RoleDefinition
from aipinho.services.policy_kernel.action_registry_service import ActionRegistryService
from aipinho.services.policy_kernel.policy_precedence_service import PolicyPrecedenceService
from aipinho.services.policy_kernel.policy_trace_service import PolicyTraceService


@dataclass(frozen=True)
class PolicyContext:
    request: PolicyResolveRequest
    normalized_actions: list[str]
    unknown_actions: list[str]
    role: RoleDefinition
    policy_order: list[str]
    violations: list[PolicyViolation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    trace: list[PolicyTraceItem] = field(default_factory=list)


class PolicyContextBuilder:
    def __init__(
        self,
        action_registry: ActionRegistryService | None = None,
        role_registry: RoleRegistry | None = None,
        policy_precedence: PolicyPrecedenceService | None = None,
        trace_service: PolicyTraceService | None = None,
    ) -> None:
        self.action_registry = action_registry or ActionRegistryService().load()
        self.role_registry = role_registry or RoleRegistry(action_registry=self.action_registry).load()
        self.policy_precedence = policy_precedence or PolicyPrecedenceService().load()
        self.trace_service = trace_service or PolicyTraceService()

    def build(self, request: PolicyResolveRequest) -> PolicyContext:
        normalized: list[str] = []
        unknown: list[str] = []
        violations: list[PolicyViolation] = []
        warnings: list[str] = []
        trace: list[PolicyTraceItem] = []

        trace.append(self.trace_service.create(
            stage="input_validation",
            rule="structured_request",
            decision="allowed",
            reason="request_schema_validated",
            source="schemas/policy/policy_decision.py",
            input={"request_id": request.request_id or ""},
        ))

        for action in request.task.requested_actions:
            try:
                canonical = self.action_registry.normalize_action(action)
                normalized.append(canonical)
                trace.append(self.trace_service.create(
                    stage="action_normalization",
                    rule="action_alias_normalization",
                    decision="allowed",
                    reason="action_normalized_to_canonical_name",
                    source="config/policies/action_registry.yaml",
                    input={"input_action": action, "canonical_action": canonical},
                ))
            except ConfigValidationError:
                unknown.append(action)
                violation = PolicyViolation(
                    code="unknown_action",
                    reason=f"Unknown action: {action}",
                    severity="error",
                    source="config/policies/action_registry.yaml",
                )
                violations.append(violation)
                trace.append(self.trace_service.create(
                    stage="action_normalization",
                    rule="unknown_action_default_deny",
                    decision="denied",
                    reason="action_not_found_in_registry",
                    severity="error",
                    source="config/policies/action_registry.yaml",
                    input={"input_action": action},
                ))

        if not request.task.requested_actions:
            trace.append(self.trace_service.create(
                stage="action_normalization",
                rule="no_actions_requested",
                decision="allowed",
                reason="conversation_or_non_tool_request",
                source="request.task.requested_actions",
            ))

        role = self.role_registry.get_role(request.role.role_id)
        policy_order = self.policy_precedence.ordered_rules()
        if request.intent.requires_workspace and not request.workspace.path:
            warnings.append("workspace_required_but_missing")

        return PolicyContext(
            request=request,
            normalized_actions=normalized,
            unknown_actions=unknown,
            role=role,
            policy_order=policy_order,
            violations=violations,
            warnings=warnings,
            trace=trace,
        )