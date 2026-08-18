from __future__ import annotations

from aipinho.schemas.semantic_runtime.isr import (
    IntermediateSemanticRepresentation,
    ISREntity,
    ISRSerializer,
    ISRValidator,
    ISRVersioning,
)
from aipinho.services.semantic_runtime.semantic_interpreter_pipeline import SemanticInterpreterPipeline


def test_isr_structural_validation_passes_for_semantic_interpreter_output():
    isr = SemanticInterpreterPipeline().run("Analise este projeto em modo read-only e gere resumo.").output

    result = ISRValidator().validate(isr)

    assert result.status == "passed"
    assert result.version == "1.0"
    assert isr.version == "1.0"
    assert isr.intent == "readonly_analysis"
    assert isinstance(isr.entities, list)
    assert isinstance(isr.permissions_requested, list)
    assert isinstance(isr.constraints, dict)
    assert isinstance(isr.expected_outputs, list)
    assert "score" in isr.ambiguity
    assert 0.0 <= isr.confidence <= 1.0
    assert isr.semantic_trace


def test_isr_versioning_rejects_unsupported_version():
    isr = IntermediateSemanticRepresentation(version="9.9", intent="conversation", scope="chat")

    result = ISRValidator(ISRVersioning(supported_versions=["1.0"])).validate(isr)

    assert result.status == "failed"
    assert "unsupported_isr_version" in result.errors


def test_isr_serializer_round_trips_without_runtime_dependencies():
    isr = IntermediateSemanticRepresentation(
        intent="readonly_analysis",
        scope="workspace_or_filesystem",
        entities=[ISREntity(entity_type="path", value=r"C:\Dev\AIpinho", confidence=0.95)],
        constraints={"read_only": True},
        expected_outputs=["report"],
        ambiguity={"score": 0.1, "reasons": []},
        confidence=0.9,
        semantic_trace=[{"stage": "test", "status": "ready"}],
    )

    payload = ISRSerializer.to_json(isr)
    restored = ISRSerializer.from_json(payload)

    assert restored.model_dump(mode="json") == isr.model_dump(mode="json")
    assert restored.task_id is None
    assert restored.approval_id is None
    assert restored.side_effects is False


def test_isr_backward_compatibility_properties_map_old_sr2_names():
    isr = IntermediateSemanticRepresentation(
        intent="conversation",
        scope="chat",
        expected_outputs=["summary"],
        ambiguity={"score": 0.25, "reasons": []},
        semantic_trace=[{"stage": "compat", "status": "ready"}],
    )

    assert isr.requested_outputs == ["summary"]
    assert isr.ambiguity_score == 0.25
    assert isr.trace == [{"stage": "compat", "status": "ready"}]
    assert isr.capability_id == "semantic_understanding"


def test_isr_validator_blocks_execution_refs_and_effects():
    isr = IntermediateSemanticRepresentation(
        intent="implementation_request",
        scope="project",
        confidence=0.8,
        ambiguity={"score": 0.2, "reasons": []},
        semantic_trace=[{"stage": "test", "status": "ready"}],
        effect_flags={"side_effects": True, "created_contract": False, "runtime_executed": False, "tools_called": False, "skills_called": False, "files_written": False, "patches_created": False},
        runtime_refs={"task_id": "task_x", "approval_id": None},
    )

    result = ISRValidator().validate(isr)

    assert result.status == "failed"
    assert "isr_must_not_have_side_effects" in result.errors
    assert "isr_must_not_reference_runtime_execution" in result.errors
