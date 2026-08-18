from __future__ import annotations

from aipinho.schemas.semantic_runtime.isr import IntermediateSemanticRepresentation, ISREntity, ISRValidator
from aipinho.services.semantic_runtime.semantic_normalizer import SemanticNormalizer


def _canonical_semantics(isr: IntermediateSemanticRepresentation) -> dict[str, object]:
    return {
        "intent": isr.intent,
        "scope": isr.scope,
        "permissions_requested": isr.permissions_requested,
        "constraints": isr.constraints,
        "expected_outputs": isr.expected_outputs,
        "entities": [entity.model_dump(mode="json") for entity in isr.entities],
    }


def test_synonyms_normalize_to_write_patch():
    normalizer = SemanticNormalizer()
    corrigir = IntermediateSemanticRepresentation(intent="corrigir", scope="workspace_or_filesystem", permissions_requested=["write_files"])
    editar = IntermediateSemanticRepresentation(intent="editar", scope="project", permissions_requested=["apply_patch"])

    first = normalizer.normalize(corrigir)
    second = normalizer.normalize(editar)

    assert first.intent == "write_patch"
    assert second.intent == "write_patch"
    assert first.permissions_requested == ["write_patch"]
    assert second.permissions_requested == ["write_patch"]


def test_paraphrases_normalize_repository_analysis_equivalently():
    normalizer = SemanticNormalizer()
    analisar = IntermediateSemanticRepresentation(
        intent="analisar",
        scope="workspace_or_filesystem",
        entities=[ISREntity(entity_type="Path", value=r"C:\Dev\AIpinho", confidence=0.95)],
        constraints={"read_only": True, "no_write": True},
        expected_outputs=["relatorio"],
    )
    auditar = IntermediateSemanticRepresentation(
        intent="auditar",
        scope="project",
        entities=[ISREntity(entity_type="path", value=r"C:\Dev\AIpinho", confidence=0.95)],
        constraints={"read_only": True, "write_forbidden": True},
        expected_outputs=["report"],
    )

    first = normalizer.normalize(analisar)
    second = normalizer.normalize(auditar)

    assert _canonical_semantics(first) == _canonical_semantics(second)
    assert first.intent == "repository_analysis"
    assert first.scope == "repository"
    assert first.expected_outputs == ["report"]
    assert first.constraints["write_forbidden"] is True


def test_normalization_is_idempotent_for_canonical_fields():
    normalizer = SemanticNormalizer()
    original = IntermediateSemanticRepresentation(
        intent="inspecionar",
        scope="workspace_or_filesystem",
        permissions_requested=["write_files", "apply_patch"],
        constraints={"no_patch": True, "no_shell": True},
        expected_outputs=["plano", "relatorio"],
        semantic_trace=[{"stage": "test", "status": "ready"}],
    )

    once = normalizer.normalize(original)
    twice = normalizer.normalize(once)

    assert _canonical_semantics(once) == _canonical_semantics(twice)


def test_normalizer_preserves_isr_independence_and_validation():
    isr = IntermediateSemanticRepresentation(
        intent="pesquise",
        scope="public_knowledge",
        expected_outputs=["resumo"],
        confidence=0.8,
        ambiguity={"score": 0.2, "reasons": []},
        semantic_trace=[{"stage": "test", "status": "ready"}],
    )

    normalized = SemanticNormalizer().normalize(isr)
    validation = ISRValidator().validate(normalized)

    assert normalized.intent == "public_knowledge_query"
    assert normalized.scope == "public_knowledge"
    assert normalized.expected_outputs == ["summary"]
    assert normalized.task_id is None
    assert normalized.approval_id is None
    assert normalized.side_effects is False
    assert validation.status == "passed"


def test_semantic_trace_records_normalization_step():
    isr = IntermediateSemanticRepresentation(intent="ajustar", scope="repo")

    normalized = SemanticNormalizer().normalize(isr)

    assert normalized.semantic_trace[-1]["stage"] == "semantic_normalization"
    assert normalized.semantic_trace[-1]["data"]["normalized_intent"] == "write_patch"
