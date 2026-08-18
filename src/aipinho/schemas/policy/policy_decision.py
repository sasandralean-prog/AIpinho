from __future__ import annotations

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel
from aipinho.schemas.intent.intent_map import IntentSummary
from aipinho.schemas.policy.effective_policy import EffectivePolicy
from aipinho.schemas.policy.policy_trace import PolicyDecisionStatus, PolicyTraceItem
from aipinho.schemas.policy.policy_violation import PolicyViolation
from aipinho.schemas.tasks.task_contract import ContractType, TaskContractInput


class WorkspaceInput(AIpinhoModel):
    path: str | None = None
    declared: bool = False


class RoleInput(AIpinhoModel):
    role_id: str = "planner"


class UserConstraints(AIpinhoModel):
    read_only: bool = False
    no_write: bool = False
    no_shell: bool = False
    no_network: bool = False


class PolicyResolveRequest(AIpinhoModel):
    request_id: str | None = None
    intent: IntentSummary = Field(default_factory=IntentSummary)
    task: TaskContractInput = Field(default_factory=TaskContractInput)
    workspace: WorkspaceInput = Field(default_factory=WorkspaceInput)
    role: RoleInput = Field(default_factory=RoleInput)
    user_constraints: UserConstraints = Field(default_factory=UserConstraints)


class PolicyDecision(AIpinhoModel):
    decision_id: str
    status: PolicyDecisionStatus
    contract_type: ContractType
    allowed_actions: list[str] = Field(default_factory=list)
    denied_actions: list[str] = Field(default_factory=list)
    approval_required_for: list[str] = Field(default_factory=list)
    granted_capabilities: list[str] = Field(default_factory=list)
    denied_capabilities: list[str] = Field(default_factory=list)
    effective_policy: EffectivePolicy
    violations: list[PolicyViolation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    trace: list[PolicyTraceItem] = Field(default_factory=list)
    safe_to_execute: bool = False
    safe_to_preview: bool = False