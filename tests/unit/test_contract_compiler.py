from __future__ import annotations

from aipinho.schemas.semantic_runtime.isr import IntermediateSemanticRepresentation, ISREntity
from aipinho.services.semantic_runtime.contract_compiler import ContractCompiler, ContractValidator, SemanticContractPipeline
from aipinho.services.semantic_runtime.semantic_normalizer import SemanticNormalizer


def _contract_semantics(bundle):
    return {
        "execution": {
            "intent": bundle.execution.intent,
            "operation_type": bundle.execution.operation_type,
            "contract_type": bundle.execution.contract_type,
            "runtime_profile": bundle.execution.runtime_profile,
            "requested_actions": bundle.execution.requested_actions,
            "requires_task": bundle.execution.requires_task,
            "read_only": bundle.execution.read_only,
            "safe_to_execute": bundle.execution.safe_to_execute,
        },
        "workspace": {
            "scope": bundle.workspace.scope,
            "workspace_refs": bundle.workspace.workspace_refs,
            "requires_workspace": bundle.workspace.requires_workspace,
            "readonly": bundle.workspace.readonly,
        },
        "approval": {
            "approval_required": bundle.approval.approval_required,
            "approval_scope": bundle.approval.approval_scope,
            "permissions_requested": bundle.approval.permissions_requested,
            "approval_id": bundle.approval.approval_id,
        },
        "artifact": {
            "expected_outputs": bundle.artifact.expected_outputs,
            "artifact_generation_requested": bundle.artifact.artifact_generation_requested,
        },
        "role": {
            "required_roles": bundle.role.required_roles,
            "required_capabilities": bundle.role.required_capabilities,
            "can_execute_runtime": bundle.role.can_execute_runtime,
        },
    }


def test_contract_compiler_generates_repository_analysis_contracts():
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

    bundle = ContractCompiler().compile(isr)

    assert bundle.status == "compiled"
    assert bundle.execution.contract_type == "readonly_analysis"
    assert bundle.execution.operation_type == "project_analysis"
    assert bundle.execution.requires_task is True
    assert bundle.execution.read_only is True
    assert bundle.execution.safe_to_execute is False
    assert bundle.workspace.workspace_refs == [r"C:\Dev\AIpinho"]
    assert bundle.approval.approval_required is False
    assert bundle.artifact.expected_outputs == ["report"]
    assert bundle.role.required_capabilities == ["semantic_understanding", "reporting"]


def test_equivalent_isrs_generate_same_contract_semantics():
    normalizer = SemanticNormalizer()
    compiler = ContractCompiler(normalizer=normalizer)
    first = normalizer.normalize(
        IntermediateSemanticRepresentation(
            intent="analisar",
            scope="workspace_or_filesystem",
            entities=[ISREntity(entity_type="path", value=r"C:\Dev\AIpinho", confidence=0.95)],
            constraints={"no_write": True},
            expected_outputs=["relatorio"],
        )
    )
    second = normalizer.normalize(
        IntermediateSemanticRepresentation(
            intent="auditar",
            scope="project",
            entities=[ISREntity(entity_type="path", value=r"C:\Dev\AIpinho", confidence=0.95)],
            constraints={"write_forbidden": True},
            expected_outputs=["report"],
        )
    )

    first_contracts = compiler.compile(first, already_normalized=True)
    second_contracts = compiler.compile(second, already_normalized=True)

    assert _contract_semantics(first_contracts) == _contract_semantics(second_contracts)


def test_write_patch_contract_requires_approval_but_does_not_execute():
    isr = IntermediateSemanticRepresentation(
        intent="write_patch",
        scope="repository",
        entities=[ISREntity(entity_type="path", value=r"C:\Dev\AIpinho", confidence=0.95)],
        permissions_requested=["write_patch"],
        expected_outputs=["patch"],
        confidence=0.85,
        ambiguity={"score": 0.15, "reasons": []},
        semantic_trace=[{"stage": "test", "status": "ready"}],
    )

    bundle = ContractCompiler().compile(isr)

    assert bundle.execution.contract_type == "patch_request"
    assert bundle.execution.safe_to_execute is False
    assert bundle.approval.approval_required is True
    assert bundle.approval.approval_id is None
    assert bundle.role.can_execute_runtime is False


def test_contract_validator_blocks_execution_enabled_contract():
    bundle = ContractCompiler().compile(IntermediateSemanticRepresentation(intent="conversation", scope="chat", semantic_trace=[{"stage": "test", "status": "ready"}]))
    bundle.execution.safe_to_execute = True

    validation = ContractValidator().validate(bundle)

    assert validation.status == "failed"
    assert "contract_compiler_must_not_enable_execution" in validation.errors


def test_contract_pipeline_adapts_to_intent_map_without_prompt_after_interpretation():
    result = SemanticContractPipeline().compile_prompt(
        r'Analise em modo read-only o workspace "C:\Dev\AIpinho" e gere relatorio.'
    )

    adapter = result["intent_map_adapter"]
    contracts = result["contracts"]

    assert result["prompt_used_after_interpretation"] is False
    assert adapter is not None
    assert adapter["source"] == "semantic_contract_pipeline"
    assert adapter["prompt_used"] is False
    assert adapter["contract_bundle_id"] == contracts["bundle_id"]
    assert adapter["intent_type"] == contracts["execution"]["intent"]
    assert contracts["execution"]["safe_to_execute"] is False
