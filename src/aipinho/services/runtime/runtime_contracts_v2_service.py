from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.runtime.runtime_contracts_v2 import (
    ApprovalContract,
    ArtifactContract,
    ContractSerializer,
    ContractVersion,
    ExecutionContract,
    RoleContract,
    RuntimeContractBundle,
    RuntimeContractValidationResult,
    SkillContract,
    ToolContract,
    ValidationContract,
    WorkspaceContract,
)
from aipinho.schemas.semantic_runtime.contracts import CanonicalRuntimeContracts
from aipinho.utils.yaml_loader import load_yaml_file


class RuntimeContractValidator:
    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or load_yaml_file(PATHS.config_root / "runtime" / "runtime_contracts_v2.yaml", critical=True, root=PATHS.config_root / "runtime")

    def validate(self, bundle: RuntimeContractBundle) -> RuntimeContractValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        version_policy = self.config.get("contract_version", {}) if isinstance(self.config.get("contract_version", {}), dict) else {}
        supported = {str(item) for item in version_policy.get("supported", ["2.0"])}
        if bundle.contract_version.version not in supported:
            errors.append("unsupported_runtime_contract_version")
        if bundle.execution.safe_to_execute:
            errors.append("runtime_contract_compiler_must_not_enable_execution")
        if bundle.tool.tool_invocation_allowed:
            errors.append("tool_invocation_must_be_disabled_by_default")
        if bundle.skill.skill_invocation_allowed:
            errors.append("skill_invocation_must_be_disabled_by_default")
        if bundle.approval.approval_id:
            errors.append("runtime_contract_compiler_must_not_create_approval")
        forbidden = set(self._forbidden_field_names())
        dumped = bundle.model_dump(mode="json")
        found = self._find_forbidden_keys(dumped, forbidden)
        if found:
            errors.extend([f"forbidden_prompt_or_free_text_field:{item}" for item in sorted(found)])
        if bundle.role.can_execute_runtime:
            errors.append("role_contract_must_not_execute_runtime")
        if not bundle.execution.deterministic:
            errors.append("runtime_contract_must_be_deterministic")
        if bundle.execution.read_only and bundle.execution.requested_actions:
            warnings.append("readonly_contract_has_requested_actions")
        return RuntimeContractValidationResult(status="failed" if errors else "passed", errors=list(dict.fromkeys(errors)), warnings=list(dict.fromkeys(warnings)))

    def _forbidden_field_names(self) -> list[str]:
        validation = self.config.get("validation", {}) if isinstance(self.config.get("validation", {}), dict) else {}
        return [str(item) for item in validation.get("forbidden_field_names", [])]

    def _find_forbidden_keys(self, value: Any, forbidden: set[str]) -> set[str]:
        found: set[str] = set()
        if isinstance(value, dict):
            for key, item in value.items():
                if str(key) in forbidden:
                    found.add(str(key))
                found.update(self._find_forbidden_keys(item, forbidden))
        elif isinstance(value, list):
            for item in value:
                found.update(self._find_forbidden_keys(item, forbidden))
        return found


class ContractCompatibilityLayer:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "runtime" / "runtime_contracts_v2.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        version_policy = self.config.get("contract_version", {}) if isinstance(self.config.get("contract_version", {}), dict) else {}
        self.version = str(version_policy.get("current", "2.0"))

    def from_semantic_contracts(self, contracts: CanonicalRuntimeContracts) -> RuntimeContractBundle:
        execution = ExecutionContract(
            contract_version=ContractVersion(version=self.version, schema_name="ExecutionContract"),
            operation_type=contracts.execution.operation_type,
            contract_type=contracts.execution.contract_type,
            runtime_profile=contracts.execution.runtime_profile,
            requested_actions=list(contracts.execution.requested_actions),
            requires_task=contracts.execution.requires_task,
            read_only=contracts.execution.read_only,
            safe_to_execute=False,
            deterministic=True,
            metadata={"source_execution_contract_id": contracts.execution.contract_id},
        )
        workspace = WorkspaceContract(
            contract_version=ContractVersion(version=self.version, schema_name="WorkspaceContract"),
            scope=contracts.workspace.scope,
            workspace_refs=list(contracts.workspace.workspace_refs),
            requires_workspace=contracts.workspace.requires_workspace,
            readonly=contracts.workspace.readonly,
            target_paths=[],
            metadata={"source_workspace_contract_id": contracts.workspace.contract_id},
        )
        approval = ApprovalContract(
            contract_version=ContractVersion(version=self.version, schema_name="ApprovalContract"),
            approval_required=contracts.approval.approval_required,
            approval_scope=contracts.approval.approval_scope,
            permissions_requested=list(contracts.approval.permissions_requested),
            approval_id=None,
            metadata={"source_approval_contract_id": contracts.approval.contract_id},
        )
        artifact = ArtifactContract(
            contract_version=ContractVersion(version=self.version, schema_name="ArtifactContract"),
            expected_outputs=list(contracts.artifact.expected_outputs),
            artifact_generation_requested=contracts.artifact.artifact_generation_requested,
            logical_paths=list(contracts.artifact.logical_paths),
            metadata={"source_artifact_contract_id": contracts.artifact.contract_id},
        )
        validation = ValidationContract(
            contract_version=ContractVersion(version=self.version, schema_name="ValidationContract"),
            validation_required=contracts.validation.validation_required,
            required_checks=list(contracts.validation.required_checks),
            success_criteria=list(contracts.validation.success_criteria),
            metadata={"source_validation_contract_id": contracts.validation.contract_id},
        )
        role = RoleContract(
            contract_version=ContractVersion(version=self.version, schema_name="RoleContract"),
            required_roles=list(contracts.role.required_roles),
            required_capabilities=list(contracts.role.required_capabilities),
            can_call_tools=False,
            can_write=contracts.role.can_write,
            can_execute_runtime=False,
            metadata={"source_role_contract_id": contracts.role.contract_id},
        )
        version = ContractVersion(version=self.version, schema_name="RuntimeContractBundle")
        return RuntimeContractBundle(
            contract_version=version,
            status=contracts.status,
            source_contract_bundle_id=contracts.bundle_id,
            execution=execution,
            workspace=workspace,
            approval=approval,
            artifact=artifact,
            validation=validation,
            role=role,
            tool=ToolContract(contract_version=ContractVersion(version=self.version, schema_name="ToolContract"), tools_denied=list(execution.requested_actions), tool_invocation_allowed=False),
            skill=SkillContract(contract_version=ContractVersion(version=self.version, schema_name="SkillContract"), skill_invocation_allowed=False, placeholder=True),
            warnings=list(contracts.warnings),
            blocked_reasons=list(contracts.blocked_reasons),
            trace=[*contracts.trace, {"stage": "runtime_contracts_v2_compatibility", "status": "converted"}],
        )

    def to_legacy_semantic_contracts(self, bundle: RuntimeContractBundle) -> dict[str, Any]:
        return {
            "source": "runtime_contracts_v2_compatibility_layer",
            "version": bundle.contract_version.version,
            "operation_type": bundle.execution.operation_type,
            "contract_type": bundle.execution.contract_type,
            "runtime_profile": bundle.execution.runtime_profile,
            "requested_actions": list(bundle.execution.requested_actions),
            "requires_task": bundle.execution.requires_task,
            "requires_workspace": bundle.workspace.requires_workspace,
            "requires_approval": bundle.approval.approval_required,
            "expected_outputs": list(bundle.artifact.expected_outputs),
            "safe_to_execute": False,
        }


class RuntimeContractsV2Service:
    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "runtime" / "runtime_contracts_v2.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.compatibility = ContractCompatibilityLayer(self.config_path)
        self.validator = RuntimeContractValidator(self.config)

    def enabled(self) -> bool:
        raw = self.config.get("governed_runtime_contracts_v2", {}) if isinstance(self.config.get("governed_runtime_contracts_v2", {}), dict) else {}
        return bool(raw.get("enabled", False))

    def from_semantic_contracts(self, contracts: CanonicalRuntimeContracts) -> RuntimeContractBundle:
        bundle = self.compatibility.from_semantic_contracts(contracts)
        validation = self.validator.validate(bundle)
        if validation.status == "failed":
            bundle.status = "blocked"
            bundle.blocked_reasons = list(dict.fromkeys([*bundle.blocked_reasons, *validation.errors]))
        bundle.warnings = list(dict.fromkeys([*bundle.warnings, *validation.warnings]))
        return bundle

    def serialize(self, bundle: RuntimeContractBundle) -> str:
        return ContractSerializer.to_json(bundle)

    def deserialize(self, payload: str) -> RuntimeContractBundle:
        return ContractSerializer.from_json(payload)

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "runtime_contracts_v2",
            "enabled": self.enabled(),
            "config": str(self.config_path),
        }
