from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.semantic_runtime.contracts import (
    ApprovalContract,
    ArtifactContract,
    CanonicalRuntimeContracts,
    ContractValidationResult,
    ContractVersioning,
    ExecutionContract,
    RoleContract,
    SemanticIntentMapAdapter,
    ValidationContract,
    WorkspaceContract,
)
from aipinho.schemas.semantic_runtime.isr import IntermediateSemanticRepresentation, ISRValidator
from aipinho.services.semantic_runtime.semantic_interpreter_pipeline import SemanticInterpreterPipeline
from aipinho.services.semantic_runtime.semantic_normalizer import SemanticNormalizer
from aipinho.utils.yaml_loader import load_yaml_file


class ExecutionContractBuilder:
    def build(self, isr: IntermediateSemanticRepresentation, policy: dict[str, Any]) -> ExecutionContract:
        requested_actions = [] if self._forbids_write(isr) else list(policy.get("requested_actions", []) or [])
        read_only = bool(policy.get("read_only", True)) or self._forbids_write(isr)
        return ExecutionContract(
            isr_id=isr.isr_id,
            intent=isr.intent,
            operation_type=str(policy.get("operation_type", "unknown")),
            contract_type=str(policy.get("contract_type", "unknown")),
            runtime_profile=policy.get("runtime_profile"),
            requested_actions=requested_actions,
            requires_task=bool(policy.get("requires_task", False)),
            read_only=read_only,
            safe_to_execute=False,
        )

    def _forbids_write(self, isr: IntermediateSemanticRepresentation) -> bool:
        constraints = isr.constraints
        return bool(
            constraints.get("read_only")
            or constraints.get("write_forbidden")
            or constraints.get("patch_forbidden")
            or constraints.get("runtime_forbidden")
        )


class WorkspaceContractBuilder:
    def build(self, isr: IntermediateSemanticRepresentation, execution: ExecutionContract) -> WorkspaceContract:
        workspace_refs = [entity.value for entity in isr.entities if entity.entity_type in {"path", "workspace"}]
        return WorkspaceContract(
            isr_id=isr.isr_id,
            scope=isr.scope,
            workspace_refs=workspace_refs,
            requires_workspace=execution.requires_task and isr.scope == "repository",
            readonly=execution.read_only,
        )


class ApprovalContractBuilder:
    def build(self, isr: IntermediateSemanticRepresentation, execution: ExecutionContract, policy: dict[str, Any]) -> ApprovalContract:
        approval_scope = policy.get("approval_scope")
        permissions = list(isr.permissions_requested or execution.requested_actions)
        approval_required = bool(permissions and not execution.read_only and approval_scope)
        return ApprovalContract(
            isr_id=isr.isr_id,
            approval_required=approval_required,
            approval_scope=str(approval_scope) if approval_scope and approval_required else None,
            permissions_requested=permissions if approval_required else [],
            approval_id=None,
        )


class ArtifactContractBuilder:
    def build(self, isr: IntermediateSemanticRepresentation) -> ArtifactContract:
        expected_outputs = list(isr.expected_outputs)
        return ArtifactContract(
            isr_id=isr.isr_id,
            expected_outputs=expected_outputs,
            artifact_generation_requested=bool({"report", "artifact", "file", "apk"} & set(expected_outputs)),
            logical_paths=[output for output in expected_outputs if "/" in output or "\\" in output],
        )


class ValidationContractBuilder:
    def build(self, isr: IntermediateSemanticRepresentation, policy: dict[str, Any], artifact: ArtifactContract) -> ValidationContract:
        checks = list(policy.get("required_checks", []) or [])
        if artifact.expected_outputs and "artifact_expectations" not in checks:
            checks.append("artifact_expectations")
        return ValidationContract(
            isr_id=isr.isr_id,
            validation_required=True,
            required_checks=sorted(set(checks)),
            success_criteria=["contracts_structurally_valid", "no_runtime_execution"],
        )


class RoleContractBuilder:
    def build(self, isr: IntermediateSemanticRepresentation, policy: dict[str, Any], execution: ExecutionContract) -> RoleContract:
        return RoleContract(
            isr_id=isr.isr_id,
            required_roles=list(policy.get("required_roles", []) or []),
            required_capabilities=list(policy.get("required_capabilities", []) or []),
            can_call_tools=False,
            can_write=not execution.read_only and bool(execution.requested_actions),
            can_execute_runtime=False,
        )


class ContractValidator:
    def __init__(self, versioning: ContractVersioning | None = None) -> None:
        self.versioning = versioning or ContractVersioning()

    def validate(self, contracts: CanonicalRuntimeContracts) -> ContractValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        if contracts.version not in self.versioning.supported_versions:
            errors.append("unsupported_contract_version")
        if contracts.execution.safe_to_execute:
            errors.append("contract_compiler_must_not_enable_execution")
        if contracts.role.can_execute_runtime:
            errors.append("role_contract_must_not_execute_runtime")
        if contracts.approval.approval_id:
            errors.append("contract_compiler_must_not_create_approval")
        if contracts.execution.isr_id != contracts.isr_id:
            errors.append("execution_contract_isr_mismatch")
        if contracts.artifact.isr_id != contracts.isr_id:
            errors.append("artifact_contract_isr_mismatch")
        if contracts.execution.contract_type == "unknown":
            warnings.append("unknown_contract_type")
        return ContractValidationResult(status="failed" if errors else "passed", version=contracts.version, errors=errors, warnings=warnings)


class ContractCompiler:
    def __init__(self, config_path: Path | None = None, normalizer: SemanticNormalizer | None = None) -> None:
        self.config_path = config_path or PATHS.config_root / "semantic_runtime" / "contract_compiler.yaml"
        self.config = load_yaml_file(self.config_path, critical=True, root=self.config_path.parent)
        self.normalizer = normalizer or SemanticNormalizer()
        contracts = self.config.get("contracts", {}) if isinstance(self.config.get("contracts", {}), dict) else {}
        self.versioning = ContractVersioning(
            current_version=str(contracts.get("version", "1.0")),
            supported_versions=[str(item) for item in contracts.get("supported_versions", ["1.0"])],
        )
        self.isr_validator = ISRValidator()
        self.execution_builder = ExecutionContractBuilder()
        self.workspace_builder = WorkspaceContractBuilder()
        self.approval_builder = ApprovalContractBuilder()
        self.artifact_builder = ArtifactContractBuilder()
        self.validation_builder = ValidationContractBuilder()
        self.role_builder = RoleContractBuilder()
        self.contract_validator = ContractValidator(self.versioning)

    def compile(self, isr: IntermediateSemanticRepresentation, *, already_normalized: bool = False) -> CanonicalRuntimeContracts:
        normalized = isr if already_normalized else self.normalizer.normalize(isr)
        isr_validation = self.isr_validator.validate(normalized)
        if isr_validation.status == "failed":
            return self._blocked(normalized, isr_validation.errors)
        policy = self._policy_for(normalized.intent)
        execution = self.execution_builder.build(normalized, policy)
        workspace = self.workspace_builder.build(normalized, execution)
        approval = self.approval_builder.build(normalized, execution, policy)
        artifact = self.artifact_builder.build(normalized)
        validation = self.validation_builder.build(normalized, policy, artifact)
        role = self.role_builder.build(normalized, policy, execution)
        bundle = CanonicalRuntimeContracts(
            version=self.versioning.current_version,
            isr_id=normalized.isr_id,
            execution=execution,
            workspace=workspace,
            approval=approval,
            artifact=artifact,
            validation=validation,
            role=role,
            warnings=list(isr_validation.warnings),
            trace=[{"stage": "contract_compiler", "status": "compiled", "intent": normalized.intent}],
        )
        contract_validation = self.contract_validator.validate(bundle)
        if contract_validation.status == "failed":
            bundle.status = "blocked"
            bundle.blocked_reasons.extend(contract_validation.errors)
        bundle.warnings = list(dict.fromkeys([*bundle.warnings, *contract_validation.warnings]))
        return bundle

    def to_intent_map_adapter(self, contracts: CanonicalRuntimeContracts) -> SemanticIntentMapAdapter:
        execution = contracts.execution
        return SemanticIntentMapAdapter(
            intent_type=execution.intent,
            operation_type=execution.operation_type,
            contract_type=execution.contract_type,
            task_type=execution.contract_type,
            requires_task=execution.requires_task,
            requires_workspace=contracts.workspace.requires_workspace,
            requires_approval=contracts.approval.approval_required,
            requested_actions=execution.requested_actions,
            workspace_refs=contracts.workspace.workspace_refs,
            expected_outputs=contracts.artifact.expected_outputs,
            isr_id=contracts.isr_id,
            contract_bundle_id=contracts.bundle_id,
        )

    def semantic_contract_pipeline_enabled(self) -> bool:
        raw = self.config.get("semantic_contract_pipeline", {}) if isinstance(self.config.get("semantic_contract_pipeline", {}), dict) else {}
        return bool(raw.get("enabled", False))

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "contract_compiler",
            "semantic_contract_pipeline": self.semantic_contract_pipeline_enabled(),
            "version": self.versioning.current_version,
        }

    def _policy_for(self, intent: str) -> dict[str, Any]:
        raw = self.config.get("intent_contracts", {}) if isinstance(self.config.get("intent_contracts", {}), dict) else {}
        value = raw.get(intent) or raw.get("unknown") or {}
        return value if isinstance(value, dict) else {}

    def _blocked(self, isr: IntermediateSemanticRepresentation, reasons: list[str]) -> CanonicalRuntimeContracts:
        policy = self._policy_for("unknown")
        execution = self.execution_builder.build(isr, policy)
        workspace = self.workspace_builder.build(isr, execution)
        artifact = self.artifact_builder.build(isr)
        validation = self.validation_builder.build(isr, policy, artifact)
        role = self.role_builder.build(isr, policy, execution)
        return CanonicalRuntimeContracts(
            version=self.versioning.current_version,
            status="blocked",
            isr_id=isr.isr_id,
            execution=execution,
            workspace=workspace,
            approval=ApprovalContract(isr_id=isr.isr_id),
            artifact=artifact,
            validation=validation,
            role=role,
            blocked_reasons=reasons,
            trace=[{"stage": "contract_compiler", "status": "blocked", "reasons": reasons}],
        )


class SemanticContractPipeline:
    def __init__(self, interpreter: SemanticInterpreterPipeline | None = None, normalizer: SemanticNormalizer | None = None, compiler: ContractCompiler | None = None) -> None:
        self.interpreter = interpreter or SemanticInterpreterPipeline()
        self.normalizer = normalizer or SemanticNormalizer()
        self.compiler = compiler or ContractCompiler(normalizer=self.normalizer)

    def compile_prompt(self, prompt: str, *, session_id: str | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
        interpretation = self.interpreter.run(prompt, session_id=session_id, context=context)
        normalized = self.normalizer.normalize(interpretation.output)
        contracts = self.compiler.compile(normalized, already_normalized=True)
        adapter = self.compiler.to_intent_map_adapter(contracts) if self.compiler.semantic_contract_pipeline_enabled() else None
        return {
            "isr": normalized.model_dump(mode="json"),
            "contracts": contracts.model_dump(mode="json"),
            "intent_map_adapter": adapter.model_dump(mode="json") if adapter else None,
            "prompt_used_after_interpretation": False,
        }
