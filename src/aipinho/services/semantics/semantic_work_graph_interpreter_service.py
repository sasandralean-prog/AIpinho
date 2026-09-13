from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from aipinho.schemas.semantics.semantic_execution_graph import (
    SemanticWorkDecompositionCandidate,
    SemanticWorkDecompositionResult,
)
from aipinho.services.semantics.contract_bound_semantic_reasoner import (
    ContractBoundSemanticReasoner,
)
from aipinho.services.semantics.semantic_execution_graph_compiler_service import (
    SemanticExecutionGraphCompilerService,
)
from aipinho.services.semantics.task_semantic_vocabulary_authority_service import (
    TaskSemanticVocabularyAuthorityService,
)


class SemanticWorkGraphInterpreterService:
    """Uses a model to propose work semantics; deterministic compiler decides."""

    def __init__(
        self,
        *,
        reasoner: ContractBoundSemanticReasoner | None = None,
        compiler: SemanticExecutionGraphCompilerService | None = None,
        vocabulary_authority: TaskSemanticVocabularyAuthorityService | None = None,
    ) -> None:
        self.reasoner = reasoner
        self.compiler = compiler or SemanticExecutionGraphCompilerService()
        self.vocabulary_authority = (
            vocabulary_authority or TaskSemanticVocabularyAuthorityService()
        )

    def interpret_for_run(self, *, run: Any) -> SemanticWorkDecompositionResult:
        structural = self.compiler.compile_structural_for_run(run=run)
        if structural.status != "accepted" or structural.graph is None:
            return structural
        if structural.graph.status == "ready":
            structural.status = "not_required"
            structural.provenance["interpretation"] = "explicit_work_modes"
            return structural

        plan = getattr(run, "plan", None)
        canonical = getattr(plan, "canonical_execution_plan", None)
        vocabulary = getattr(plan, "task_semantic_vocabulary", None)
        if canonical is None or vocabulary is None:
            return SemanticWorkDecompositionResult(
                status="insufficient_evidence",
                reason_code="SEMANTIC_WORK_DECOMPOSITION_CANONICAL_CONTEXT_REQUIRED",
            )
        if not self.vocabulary_authority.verify(vocabulary):
            return SemanticWorkDecompositionResult(
                status="insufficient_evidence",
                reason_code="SEMANTIC_WORK_DECOMPOSITION_VOCABULARY_AUTHORITY_INVALID",
            )

        reasoner = self.reasoner or ContractBoundSemanticReasoner()
        self.reasoner = reasoner
        governed = self.vocabulary_authority.governed_view(vocabulary)
        steps = [
            {
                "step_id": step.step_id,
                "step_type": step.step_type,
                "action": step.action,
                "required": step.required,
                "side_effect": step.side_effect,
                "depends_on": list(step.depends_on),
                "expected_outputs": list(step.expected_outputs),
                "required_capabilities": list(step.required_capabilities),
                "metadata": dict(step.metadata),
            }
            for step in canonical.execution_steps
        ]
        proposal = reasoner.propose_json(
            semantic_goal=(
                "Decompose the canonical execution plan into semantic work units. "
                "Classify approaches without using phase numbers as semantics."
            ),
            payload={
                "canonical_task": {
                    "semantic_goal": canonical.semantic_goal,
                    "operation_kind": canonical.operation_kind,
                    "semantic_intent_graph": dict(
                        canonical.metadata.get("semantic_intent_graph") or {}
                    ),
                    "steps": steps,
                },
                "governed_vocabulary": {
                    "work_modes": governed.get("work_modes", []),
                    "capability_identifiers": governed.get(
                        "capability_identifiers",
                        [],
                    ),
                    "effect_identifiers": governed.get(
                        "effect_identifiers",
                        [],
                    ),
                },
                "output_schema": {
                    "work_units": [
                        {
                            "unit_key": "machine_identifier",
                            "source_step_ids": ["existing_step_id"],
                            "semantic_goal": "description",
                            "work_modes": ["governed_work_mode"],
                            "required_capabilities": [
                                "exact_capabilities_of_source_steps"
                            ],
                            "requested_effects": ["governed_effect"],
                            "prohibited_effects": ["governed_effect"],
                        }
                    ],
                    "edges": [
                        {
                            "producer_unit_key": "existing_unit_key",
                            "consumer_unit_key": "existing_unit_key",
                            "relation": (
                                "semantic_dependency|evidence_dependency|"
                                "validation_dependency|context_dependency|"
                                "ordering_constraint"
                            ),
                            "required": "boolean",
                        }
                    ],
                    "confidence": "number_between_0_and_1",
                    "rationale": "non_empty_string",
                },
                "rules": [
                    "Cover every canonical source step exactly once.",
                    "Never invent or omit source step ids.",
                    "A unit may group multiple steps only when they form one semantic work unit.",
                    "Select work_modes only from governed_vocabulary.work_modes.",
                    "required_capabilities must exactly equal the union of capabilities of the unit source steps.",
                    "Select effects only from governed_vocabulary.effect_identifiers.",
                    "Preserve every explicit canonical depends_on relation across units.",
                    "Do not create a linear chain merely because steps are listed in order.",
                    "Do not use phase numbers, filenames, deliverables, or unit positions as semantic authority.",
                    "unit_key is only a local reference label and grants no semantic meaning.",
                    "If decomposition is uncertain, lower confidence rather than inventing semantics.",
                    "Do not authorize execution or mutate the plan.",
                ],
            },
            allowed_fields=["work_units", "edges", "confidence", "rationale"],
            required_fields=["work_units", "edges", "confidence", "rationale"],
        )
        provenance = {
            "model_id": proposal.get("model_id"),
            "response_id": proposal.get("response_id"),
            "real_inference": proposal.get("real_inference"),
            "evaluation_status": proposal.get("evaluation_status"),
            "warnings": list(proposal.get("warnings") or []),
            "authority": "deterministic_semantic_graph_gate",
        }
        if proposal.get("status") != "candidate":
            return SemanticWorkDecompositionResult(
                status="insufficient_evidence",
                reason_code=str(
                    proposal.get("reason_code")
                    or "SEMANTIC_WORK_DECOMPOSITION_MODEL_UNAVAILABLE"
                ),
                provenance=provenance,
            )
        try:
            candidate = SemanticWorkDecompositionCandidate.model_validate(
                proposal.get("candidate") or {}
            )
        except ValidationError:
            return SemanticWorkDecompositionResult(
                status="insufficient_evidence",
                reason_code="SEMANTIC_WORK_DECOMPOSITION_CANDIDATE_INVALID",
                candidate=dict(proposal.get("candidate") or {}),
                provenance=provenance,
            )
        return self.compiler.compile_candidate_for_run(
            run=run,
            candidate=candidate,
            provenance=provenance,
        )
