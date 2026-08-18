from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import Field

from aipinho.schemas.common.base import AIpinhoModel


RuntimeContractStatus = Literal["compiled", "blocked"]


class ContractVersion(AIpinhoModel):
    version: str = "2.0"
    schema_name: str
    compatible_from: str = "2.0"
    extensions: dict[str, Any] = Field(default_factory=dict)


class ExecutionContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"rt_exec_{uuid4().hex}")
    contract_version: ContractVersion = Field(default_factory=lambda: ContractVersion(schema_name="ExecutionContract"))
    operation_type: str
    contract_type: str
    runtime_profile: str | None = None
    requested_actions: list[str] = Field(default_factory=list)
    requires_task: bool = False
    read_only: bool = True
    safe_to_execute: bool = False
    deterministic: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkspaceContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"rt_workspace_{uuid4().hex}")
    contract_version: ContractVersion = Field(default_factory=lambda: ContractVersion(schema_name="WorkspaceContract"))
    scope: str
    workspace_refs: list[str] = Field(default_factory=list)
    requires_workspace: bool = False
    readonly: bool = True
    target_paths: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ApprovalContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"rt_approval_{uuid4().hex}")
    contract_version: ContractVersion = Field(default_factory=lambda: ContractVersion(schema_name="ApprovalContract"))
    approval_required: bool = False
    approval_scope: str | None = None
    permissions_requested: list[str] = Field(default_factory=list)
    approval_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ArtifactContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"rt_artifact_{uuid4().hex}")
    contract_version: ContractVersion = Field(default_factory=lambda: ContractVersion(schema_name="ArtifactContract"))
    expected_outputs: list[str] = Field(default_factory=list)
    artifact_generation_requested: bool = False
    logical_paths: list[str] = Field(default_factory=list)
    retention_policy: str = "runtime_default"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ValidationContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"rt_validation_{uuid4().hex}")
    contract_version: ContractVersion = Field(default_factory=lambda: ContractVersion(schema_name="ValidationContract"))
    validation_required: bool = True
    required_checks: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RoleContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"rt_role_{uuid4().hex}")
    contract_version: ContractVersion = Field(default_factory=lambda: ContractVersion(schema_name="RoleContract"))
    required_roles: list[str] = Field(default_factory=list)
    required_capabilities: list[str] = Field(default_factory=list)
    can_call_tools: bool = False
    can_write: bool = False
    can_execute_runtime: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"rt_tool_{uuid4().hex}")
    contract_version: ContractVersion = Field(default_factory=lambda: ContractVersion(schema_name="ToolContract"))
    tools_allowed: list[str] = Field(default_factory=list)
    tools_denied: list[str] = Field(default_factory=list)
    tool_invocation_allowed: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class SkillContract(AIpinhoModel):
    contract_id: str = Field(default_factory=lambda: f"rt_skill_{uuid4().hex}")
    contract_version: ContractVersion = Field(default_factory=lambda: ContractVersion(schema_name="SkillContract"))
    skills_allowed: list[str] = Field(default_factory=list)
    skills_denied: list[str] = Field(default_factory=list)
    skill_invocation_allowed: bool = False
    placeholder: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class RuntimeContractBundle(AIpinhoModel):
    bundle_id: str = Field(default_factory=lambda: f"runtime_contract_bundle_{uuid4().hex}")
    contract_version: ContractVersion = Field(default_factory=lambda: ContractVersion(schema_name="RuntimeContractBundle"))
    status: RuntimeContractStatus = "compiled"
    source_contract_bundle_id: str | None = None
    execution: ExecutionContract
    workspace: WorkspaceContract
    approval: ApprovalContract
    artifact: ArtifactContract
    validation: ValidationContract
    role: RoleContract
    tool: ToolContract = Field(default_factory=ToolContract)
    skill: SkillContract = Field(default_factory=SkillContract)
    warnings: list[str] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)
    trace: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    extensions: dict[str, Any] = Field(default_factory=dict)


class RuntimeContractValidationResult(AIpinhoModel):
    status: Literal["passed", "failed"] = "passed"
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ContractSerializer:
    @staticmethod
    def to_dict(bundle: RuntimeContractBundle) -> dict[str, Any]:
        return bundle.model_dump(mode="json")

    @staticmethod
    def to_json(bundle: RuntimeContractBundle) -> str:
        return json.dumps(ContractSerializer.to_dict(bundle), ensure_ascii=False, sort_keys=True)

    @staticmethod
    def from_dict(data: dict[str, Any]) -> RuntimeContractBundle:
        return RuntimeContractBundle.model_validate(data)

    @staticmethod
    def from_json(payload: str) -> RuntimeContractBundle:
        return RuntimeContractBundle.model_validate_json(payload)
