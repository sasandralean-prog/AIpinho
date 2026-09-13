from __future__ import annotations

from types import SimpleNamespace

from aipinho.schemas.runtime.execution_plan import CanonicalExecutionPlan, CanonicalExecutionStep
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.semantics.task_semantic_vocabulary import (
    SemanticConceptDefinition,
    SemanticConceptProvenance,
    TaskSemanticVocabularyRevisionRequest,
)
from aipinho.services.semantics.task_semantic_vocabulary_authority_service import (
    TaskSemanticVocabularyAuthorityService,
)
from aipinho.services.semantics.task_semantic_vocabulary_compiler_service import (
    TaskSemanticVocabularyCompilerService,
)
from aipinho.services.semantics.task_semantic_vocabulary_revision_service import (
    TaskSemanticVocabularyRevisionService,
)


def _run(*, capability: str = "validation", intent_map: dict | None = None):
    step = CanonicalExecutionStep(
        step_id="step_validation",
        step_type="validation",
        action="validate_runtime",
        side_effect=False,
        required_capabilities=[capability],
    )
    canonical = CanonicalExecutionPlan(
        semantic_goal="validate a governed result",
        operation_kind="validation",
        execution_steps=[step],
        required_capabilities=[capability],
        rollback_strategy={},
        trace_id="trace_vocab",
        metadata={
            "semantic_intent_graph": {
                "knowledge_output": True,
                "readonly_contract": True,
            }
        },
    )
    plan = TaskRunPlan(
        plan_id="plan_vocab",
        contract_type="validation_request",
        canonical_execution_plan=canonical,
    )
    return SimpleNamespace(
        run_id="task_run_vocab",
        task_id="task_vocab",
        plan=plan,
        intent_map=dict(intent_map or {}),
        capabilities_required=[capability],
    )


def _compile(run=None):
    result = TaskSemanticVocabularyCompilerService().compile_for_run(
        run=run or _run()
    )
    assert result.status == "compiled"
    assert result.vocabulary is not None
    return result.vocabulary


def test_compiler_freezes_stable_authority_hash() -> None:
    run = _run()
    first = _compile(run)
    second = _compile(run)

    assert first.authority_sha256 == second.authority_sha256
    assert first.vocabulary_id == second.vocabulary_id
    assert first.source_semantics_sha256 == second.source_semantics_sha256
    assert TaskSemanticVocabularyAuthorityService().verify(first)


def test_concept_identity_is_typed_not_global_by_identifier() -> None:
    vocabulary = _compile()
    matches = [
        item
        for item in vocabulary.concepts
        if item.concept_id == "validation"
    ]

    assert {item.concept_type for item in matches} == {"work_mode", "capability"}


def test_deliverable_text_is_not_promoted_to_task_concept() -> None:
    run = _run(intent_map={"requested_deliverables": ["analysis report"]})
    vocabulary = _compile(run)

    assert all(item.concept_id != "analysis report" for item in vocabulary.concepts)
    assert all(item.concept_id != "analysis_report" for item in vocabulary.concepts)


def test_explicit_typed_semantic_property_gets_epistemic_domain() -> None:
    run = _run(
        intent_map={
            "semantic_properties": {
                "document_identity": ["observed", "inferred"],
            }
        }
    )
    vocabulary = _compile(run)
    concept = next(
        item
        for item in vocabulary.concepts
        if item.concept_type == "epistemic_property"
        and item.concept_id == "document_identity"
    )

    assert "unknown" in concept.allowed_states
    assert "unknown" not in concept.requirement_states
    assert concept.requirement_states == ["observed", "inferred", "derived"]


def test_revision_is_additive_and_preserves_parent() -> None:
    parent = _compile()
    candidate = SemanticConceptDefinition(
        concept_id="content_identity",
        concept_type="epistemic_property",
        scope="task",
        allowed_states=["observed", "inferred", "unknown"],
        requirement_states=["observed", "inferred"],
        provenance=[
            SemanticConceptProvenance(
                source_kind="model_candidate",
                source_ref="fixture:model",
            )
        ],
    )
    result = TaskSemanticVocabularyRevisionService().revise(
        parent=parent,
        request=TaskSemanticVocabularyRevisionRequest(
            parent_vocabulary_id=parent.vocabulary_id,
            parent_authority_sha256=parent.authority_sha256,
            reason="new semantic concept required by work decomposition",
            source_ref="semantic_work_graph_candidate:fixture",
            concepts_to_add=[candidate],
        ),
    )

    assert result.status == "revised"
    assert result.vocabulary is not None
    revised = result.vocabulary
    assert revised.revision == parent.revision + 1
    assert revised.parent_vocabulary_id == parent.vocabulary_id
    assert revised.parent_authority_sha256 == parent.authority_sha256
    assert len(revised.concepts) == len(parent.concepts) + 1
    assert TaskSemanticVocabularyAuthorityService().verify(revised)
    assert all(item.concept_id != "content_identity" for item in parent.concepts)


def test_revision_rejects_existing_typed_identity() -> None:
    parent = _compile()
    result = TaskSemanticVocabularyRevisionService().revise(
        parent=parent,
        request=TaskSemanticVocabularyRevisionRequest(
            parent_vocabulary_id=parent.vocabulary_id,
            parent_authority_sha256=parent.authority_sha256,
            reason="attempted override",
            concepts_to_add=[
                SemanticConceptDefinition(
                    concept_id="validation",
                    concept_type="work_mode",
                    scope="task",
                )
            ],
        ),
    )

    assert result.status == "rejected"
    assert result.reason_codes == [
        "TASK_SEMANTIC_VOCABULARY_CONCEPT_ALREADY_DEFINED"
    ]


def test_revision_rejects_state_outside_type_domain() -> None:
    parent = _compile()
    result = TaskSemanticVocabularyRevisionService().revise(
        parent=parent,
        request=TaskSemanticVocabularyRevisionRequest(
            parent_vocabulary_id=parent.vocabulary_id,
            parent_authority_sha256=parent.authority_sha256,
            reason="invalid epistemic state",
            concepts_to_add=[
                SemanticConceptDefinition(
                    concept_id="content_identity",
                    concept_type="epistemic_property",
                    scope="task",
                    allowed_states=["readonly_analysis"],
                    requirement_states=["readonly_analysis"],
                )
            ],
        ),
    )

    assert result.status == "rejected"
    assert result.reason_codes == [
        "TASK_SEMANTIC_VOCABULARY_STATE_OUTSIDE_TYPE_DOMAIN"
    ]


def test_tampered_vocabulary_fails_authority_verification() -> None:
    vocabulary = _compile()
    vocabulary.concepts.append(
        SemanticConceptDefinition(
            concept_id="tampered_concept",
            concept_type="relationship",
            scope="task",
        )
    )

    assert not TaskSemanticVocabularyAuthorityService().verify(vocabulary)
