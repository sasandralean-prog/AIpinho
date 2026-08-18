from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


ContractCompilerStatus = Literal["compiled", "blocked"]


class ContractVersioning(AIpinhoModel):
    current_version: str = "1.0"
    supported_versions: list[str] = Field(default_factory=lambda: ["1.0"])


class ExecutionContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"execution_contract_{uuid4().hex}")
    version: str = "1.0"
    isr_id: str
    intent: str
    operation_type: str
    contract_type: str
    runtime_profile: str | None = None
    requested_actions: list[str] = Field(default_factory=list)
    requires_task: bool = False
    read_only: bool = True
    safe_to_execute: bool = False


class WorkspaceContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"workspace_contract_{uuid4().hex}")
    version: str = "1.0"
    isr_id: str
    scope: str
    workspace_refs: list[str] = Field(default_factory=list)
    requires_workspace: bool = False
    readonly: bool = True


class ApprovalContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"approval_contract_{uuid4().hex}")
    version: str = "1.0"
    isr_id: str
    approval_required: bool = False
    approval_scope: str | None = None
    permissions_requested: list[str] = Field(default_factory=list)
    approval_id: str | None = None


class ArtifactContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"artifact_contract_{uuid4().hex}")
    version: str = "1.0"
    isr_id: str
    expected_outputs: list[str] = Field(default_factory=list)
    artifact_generation_requested: bool = False
    logical_paths: list[str] = Field(default_factory=list)


class ValidationContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"validation_contract_{uuid4().hex}")
    version: str = "1.0"
    isr_id: str
    validation_required: bool = True
    required_checks: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)


class RoleContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"role_contract_{uuid4().hex}")
    version: str = "1.0"
    isr_id: str
    required_roles: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    can_call_tools: bool = False
    can_write: bool = False
    can_execute_runtime: bool = False


class CanonicalRuntimeContracts(AIpinhoModel):
    bundle_id: str = Field(default_factory=lambda: f"contract_bundle_{uuid4().hex}")
    version: str = "1.0"
    status: ContractCompilerStatus = "compiled"
    isr_id: str
    execution: ExecutionContract
    workspace: WorkspaceContract
    approval: ApprovalContract
    artifact: ArtifactContract
    validation: ValidationContract
    role: RoleContract
    source: str = "semantic_contract_compiler"
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ContractValidationResult(AIpinhoModel):
    status: Literal["passed", "failed"] = "passed"
    version: str | None = None
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class SemanticIntentMapAdapter(AIpinhoModel):
    source: str = "semantic_contract_pipeline"
    intent_type: str
    operation_type: str
    contract_type: str
    task_type: str
    requires_task: bool
    requires_workspace: bool
    requires_approval: bool
    requested_actions: list[str] = Field(default_factory=list)
    workspace_refs: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)
    isr_id: str
    contract_bundle_id: str
    prompt_used: bool = False
