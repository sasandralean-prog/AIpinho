from __future__ import annotations

from aipinho.schemas.runtime.runtime_contracts_v2 import (
    ContractSerializer,
    RuntimeContractBundle,
    RuntimeContractValidationResult,
)
from aipinho.schemas.semantic_runtime.isr import IntermediateSemanticRepresentation, ISREntity
from aipinho.services.runtime.runtime_contracts_v2_service import (
    ContractCompatibilityLayer,
    RuntimeContractValidator,
    RuntimeContractsV2Service,
)
from aipinho.services.semantic_runtime.contract_compiler import ContractCompiler


def _semantic_contracts():
    isr = IntermediateSemanticRepresentation(
        intent="repository_analysis",
        scope="repository",
        entities=[ISREntity(entity_type="path", value=r"C:\Dev\AIpinho", confidence=0.95)],
        constraints={"read_only": True},
        expected_outputs=["report"],
        confidence=0.9,
        ambiguity={"score": 0.1, "reasons": []},
        semantic_trace=[{"stage": "test", "status": "ready"}],
    )
    return ContractCompiler().compile(isr)


def test_runtime_contract_serialization_roundtrip():
    bundle = RuntimeContractsV2Service().from_semantic_contracts(_semantic_contracts())

    payload = ContractSerializer.to_json(bundle)
    restored = ContractSerializer.from_json(payload)

    assert restored.model_dump(mode="json") == bundle.model_dump(mode="json")
    assert restored.contract_version.version == "2.0"
    assert restored.execution.safe_to_execute is False
    assert restored.tool.tool_invocation_allowed is False
    assert restored.skill.skill_invocation_allowed is False


def test_runtime_contract_validation_blocks_prompt_fields():
    bundle = RuntimeContractsV2Service().from_semantic_contracts(_semantic_contracts())
    bundle.extensions["raw_prompt"] = "nao deve aparecer"

    result = RuntimeContractValidator().validate(bundle)

    assert result.status == "failed"
    assert "forbidden_prompt_or_free_text_field:raw_prompt" in result.errors


def test_backward_compatibility_layer_converts_sr5_contracts_to_v2():
    semantic = _semantic_contracts()
    v2 = ContractCompatibilityLayer().from_semantic_contracts(semantic)

    assert v2.source_contract_bundle_id == semantic.bundle_id
    assert v2.execution.operation_type == semantic.execution.operation_type
    assert v2.execution.contract_type == semantic.execution.contract_type
    assert v2.workspace.workspace_refs == semantic.workspace.workspace_refs
    assert v2.artifact.expected_outputs == semantic.artifact.expected_outputs
    assert v2.execution.safe_to_execute is False
    assert v2.execution.deterministic is True


def test_version_upgrade_from_v1_semantic_contracts_produces_v2_bundle():
    semantic = _semantic_contracts()

    upgraded = RuntimeContractsV2Service().from_semantic_contracts(semantic)

    assert semantic.version == "1.0"
    assert upgraded.contract_version.version == "2.0"
    assert upgraded.execution.contract_version.version == "2.0"
    assert RuntimeContractValidator().validate(upgraded).status == "passed"


def test_runtime_contract_validator_blocks_execution_and_invocation():
    bundle = RuntimeContractsV2Service().from_semantic_contracts(_semantic_contracts())
    bundle.execution.safe_to_execute = True
    bundle.tool.tool_invocation_allowed = True
    bundle.skill.skill_invocation_allowed = True

    result = RuntimeContractValidator().validate(bundle)

    assert result.status == "failed"
    assert "runtime_contract_compiler_must_not_enable_execution" in result.errors
    assert "tool_invocation_must_be_disabled_by_default" in result.errors
    assert "skill_invocation_must_be_disabled_by_default" in result.errors


def test_legacy_adapter_shape_when_runtime_contracts_v2_disabled_or_legacy_needed():
    semantic = _semantic_contracts()
    v2 = ContractCompatibilityLayer().from_semantic_contracts(semantic)
    legacy = ContractCompatibilityLayer().to_legacy_semantic_contracts(v2)

    assert legacy["source"] == "runtime_contracts_v2_compatibility_layer"
    assert legacy["version"] == "2.0"
    assert legacy["operation_type"] == "project_analysis"
    assert legacy["contract_type"] == "readonly_analysis"
    assert legacy["safe_to_execute"] is False


def test_runtime_contract_validation_result_schema():
    result = RuntimeContractValidationResult(status="passed")

    assert result.status == "passed"
    assert result.errors == []
    assert result.warnings == []
