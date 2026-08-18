from __future__ import annotations

import json
from typing import Any

from aipinho.schemas.semantic_learning import (
    SemanticConcept,
    SemanticConceptList,
    SemanticEvidence,
    SemanticKnowledgeBase,
    SemanticKnowledgeEntry,
    SemanticKnowledgeQuery,
    SemanticKnowledgeQueryResult,
    SemanticPattern,
    SemanticPatternMatch,
    SemanticPatternRecognitionRequest,
    SemanticPatternRecognitionResult,
    SemanticRecommendation,
    SemanticRecommendationRequest,
    SemanticRecommendationResult,
    SemanticCapability,
    SemanticCompetency,
    SemanticCurriculum,
    SemanticCurriculumEntry,
    SemanticCurriculumPromoteRequest,
    SemanticCurriculumResult,
    SemanticCurriculumReviewRequest,
    SemanticEvolution,
    SemanticEvidence,
    SemanticMilestone,
    SemanticPromotionCandidate,
)
from aipinho.schemas.semantic_runtime.isr import IntermediateSemanticRepresentation


CONFIDENCE_ORDER = {"low": 0, "medium": 1, "high": 2}


class SemanticKnowledgeSerializer:
    def to_dict(self, base: SemanticKnowledgeBase) -> dict[str, Any]:
        return base.model_dump(mode="json")

    def to_json(self, base: SemanticKnowledgeBase) -> str:
        return json.dumps(self.to_dict(base), ensure_ascii=False, sort_keys=True)

    def from_dict(self, payload: dict[str, Any]) -> SemanticKnowledgeBase:
        return SemanticKnowledgeBase.model_validate(payload)

    def from_json(self, payload: str) -> SemanticKnowledgeBase:
        return SemanticKnowledgeBase.model_validate_json(payload)


class SemanticKnowledgeRepository:
    def __init__(self, entries: list[SemanticKnowledgeEntry] | None = None) -> None:
        self._base = SemanticKnowledgeBase(entries=entries or self._seed_entries())

    def base(self) -> SemanticKnowledgeBase:
        return self._base

    def list_entries(self) -> list[SemanticKnowledgeEntry]:
        return list(self._base.entries)

    def list_concepts(self) -> list[SemanticConcept]:
        concepts: dict[str, SemanticConcept] = {}
        for entry in self._base.entries:
            concepts[entry.concept.concept_id] = entry.concept
        return [concepts[key] for key in sorted(concepts)]

    def _seed_entries(self) -> list[SemanticKnowledgeEntry]:
        return [
            self._entry(
                concept_id="concept_repository_analysis",
                name="Repository analysis",
                canonical_intent="repository_analysis",
                scope="repository",
                entities=["repository", "source_tree"],
                constraints={"read_only": True, "workspace_mutation": False},
                expected_outputs=["analysis_report"],
                ambiguities=["target repository may require workspace resolution"],
                confidence="high",
            ),
            self._entry(
                concept_id="concept_write_patch",
                name="Governed patch request",
                canonical_intent="write_patch",
                scope="workspace",
                entities=["file_change", "patch"],
                constraints={"requires_approval": True, "requires_executable_plan": True},
                expected_outputs=["patch_preview", "validation_result"],
                ambiguities=["target files may require context discovery"],
                confidence="high",
            ),
            self._entry(
                concept_id="concept_public_knowledge_query",
                name="Public knowledge query",
                canonical_intent="public_knowledge_query",
                scope="public_knowledge",
                entities=["public_fact", "source"],
                constraints={"workspace_mutation": False, "requires_public_source": True},
                expected_outputs=["answer_with_sources"],
                ambiguities=["freshness may require web search"],
                confidence="medium",
            ),
        ]

    def _entry(
        self,
        *,
        concept_id: str,
        name: str,
        canonical_intent: str,
        scope: str,
        entities: list[str],
        constraints: dict[str, Any],
        expected_outputs: list[str],
        ambiguities: list[str],
        confidence: str,
    ) -> SemanticKnowledgeEntry:
        concept = SemanticConcept(
            concept_id=concept_id,
            name=name,
            canonical_intent=canonical_intent,
            scope=scope,
            description=f"Reusable semantic concept for {canonical_intent}.",
            tags=[canonical_intent, scope],
        )
        isr = IntermediateSemanticRepresentation(
            intent=canonical_intent,
            scope=scope,
            entities=[],
            constraints=constraints,
            expected_outputs=expected_outputs,
            ambiguity={"score": 0.25 if confidence == "high" else 0.45, "reasons": ambiguities},
            confidence={"low": 0.35, "medium": 0.65, "high": 0.9}[confidence],
            semantic_trace=[{"stage": "semantic_knowledge_seed", "status": "ready"}],
            reasoning_summary=f"Canonical semantic representation for {canonical_intent}.",
        )
        return SemanticKnowledgeEntry(
            entry_id=f"semantic_knowledge_{canonical_intent}",
            concept=concept,
            entities_identified=entities,
            canonical_intent=canonical_intent,
            scope=scope,
            constraints=constraints,
            confidence=confidence,  # type: ignore[arg-type]
            ambiguities=ambiguities,
            isr=isr,
            evidence=[
                SemanticEvidence(
                    evidence_type="canonical_semantic_pattern",
                    summary=f"Generic semantic pattern for {canonical_intent}.",
                    refs=[f"semantic_runtime:{canonical_intent}"],
                )
            ],
            patterns=[
                SemanticPattern(
                    pattern_id=f"semantic_pattern_{canonical_intent}",
                    concept_id=concept_id,
                    canonical_intent=canonical_intent,
                    scope=scope,
                    constraints=constraints,
                    expected_outputs=expected_outputs,
                )
            ],
        )


class SemanticKnowledgeQueryService:
    def __init__(self, repository: SemanticKnowledgeRepository | None = None) -> None:
        self.repository = repository or SemanticKnowledgeRepository()

    def list_entries(self) -> SemanticKnowledgeQueryResult:
        entries = sorted(self.repository.list_entries(), key=lambda item: item.entry_id)
        return SemanticKnowledgeQueryResult(version=self.repository.base().version.version, count=len(entries), entries=entries)

    def query(self, request: SemanticKnowledgeQuery) -> SemanticKnowledgeQueryResult:
        entries = self.repository.list_entries()
        if request.canonical_intent:
            entries = [entry for entry in entries if entry.canonical_intent == request.canonical_intent]
        if request.scope:
            entries = [entry for entry in entries if entry.scope == request.scope]
        if request.concept:
            term = request.concept.lower()
            entries = [entry for entry in entries if term in entry.concept.name.lower() or term in entry.concept.concept_id.lower()]
        if request.entity:
            term = request.entity.lower()
            entries = [entry for entry in entries if any(term in entity.lower() for entity in entry.entities_identified)]
        if request.min_confidence:
            threshold = CONFIDENCE_ORDER[request.min_confidence]
            entries = [entry for entry in entries if CONFIDENCE_ORDER[entry.confidence] >= threshold]
        entries = sorted(entries, key=lambda item: (item.canonical_intent, item.entry_id))[: request.limit]
        return SemanticKnowledgeQueryResult(version=self.repository.base().version.version, count=len(entries), entries=entries)

    def concepts(self) -> SemanticConceptList:
        concepts = self.repository.list_concepts()
        return SemanticConceptList(version=self.repository.base().version.version, count=len(concepts), concepts=concepts)

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "service": "semantic_learning_knowledge_base",
            "version": self.repository.base().version.version,
            "entries": len(self.repository.list_entries()),
            "concepts": len(self.repository.list_concepts()),
            "deterministic": True,
            "stores_full_prompt": False,
            "stores_project_specific_data": False,
        }


class SemanticPatternRepository:
    def __init__(self, knowledge: SemanticKnowledgeRepository | None = None) -> None:
        self.knowledge = knowledge or SemanticKnowledgeRepository()

    def patterns(self) -> list[tuple[SemanticKnowledgeEntry, SemanticPattern]]:
        rows: list[tuple[SemanticKnowledgeEntry, SemanticPattern]] = []
        for entry in self.knowledge.list_entries():
            for pattern in entry.patterns:
                rows.append((entry, pattern))
        return rows


class SemanticPatternNormalizer:
    def normalize(self, request: SemanticPatternRecognitionRequest) -> dict[str, Any]:
        isr = request.isr if isinstance(request.isr, IntermediateSemanticRepresentation) else IntermediateSemanticRepresentation.model_validate(request.isr)
        return {
            "intent": isr.intent,
            "scope": isr.scope,
            "entities": sorted({entity.entity_type for entity in isr.entities}),
            "constraints": dict(isr.constraints),
            "expected_outputs": list(isr.expected_outputs),
            "ambiguities": list(isr.ambiguity.get("reasons", [])) if isinstance(isr.ambiguity.get("reasons", []), list) else [],
            "confidence": float(isr.confidence),
            "doctor_categories": self._doctor_categories(request.doctor_report),
            "matrix_failures": self._matrix_failures(request.regression_matrix),
        }

    def _doctor_categories(self, report: dict[str, Any]) -> list[str]:
        findings = report.get("findings", [])
        if not isinstance(findings, list):
            return []
        return list(dict.fromkeys([str(item.get("category")) for item in findings if isinstance(item, dict) and item.get("category")]))

    def _matrix_failures(self, matrix: dict[str, Any]) -> list[str]:
        rows = matrix.get("rows", [])
        if not isinstance(rows, list):
            return []
        return list(dict.fromkeys([str(item.get("category")) for item in rows if isinstance(item, dict) and item.get("status") in {"FAIL", "WARN"} and item.get("category")]))


class SemanticPatternScorer:
    def score(self, entry: SemanticKnowledgeEntry, pattern: SemanticPattern, normalized: dict[str, Any]) -> float:
        score = 0.0
        if normalized["intent"] == pattern.canonical_intent:
            score += 0.45
        if normalized["scope"] == pattern.scope:
            score += 0.2
        constraint_hits = sum(1 for key, value in pattern.constraints.items() if normalized["constraints"].get(key) == value)
        if pattern.constraints:
            score += 0.15 * (constraint_hits / len(pattern.constraints))
        expected = set(pattern.expected_outputs)
        observed = set(normalized["expected_outputs"])
        if expected and expected.intersection(observed):
            score += 0.1
        score += {"low": 0.02, "medium": 0.06, "high": 0.1}[entry.confidence]
        return min(score, 0.99)


class SemanticPatternValidator:
    def validate(self, match: SemanticPatternMatch) -> list[str]:
        errors: list[str] = []
        if match.prompt_used:
            errors.append("semantic_pattern_match_must_not_use_prompt")
        if match.modifies_runtime:
            errors.append("semantic_pattern_match_must_not_modify_runtime")
        if match.confidence < 0.0 or match.confidence > 1.0:
            errors.append("semantic_pattern_confidence_out_of_range")
        return errors


class SemanticPatternEngine:
    def __init__(
        self,
        repository: SemanticPatternRepository | None = None,
        normalizer: SemanticPatternNormalizer | None = None,
        scorer: SemanticPatternScorer | None = None,
        validator: SemanticPatternValidator | None = None,
    ) -> None:
        self.repository = repository or SemanticPatternRepository()
        self.normalizer = normalizer or SemanticPatternNormalizer()
        self.scorer = scorer or SemanticPatternScorer()
        self.validator = validator or SemanticPatternValidator()

    def recognize(self, request: SemanticPatternRecognitionRequest) -> SemanticPatternRecognitionResult:
        normalized = self.normalizer.normalize(request)
        matches: list[SemanticPatternMatch] = []
        for entry, pattern in self.repository.patterns():
            confidence = round(self.scorer.score(entry, pattern, normalized), 2)
            if confidence <= 0.0:
                continue
            match = SemanticPatternMatch(
                pattern_id=pattern.pattern_id,
                concept=entry.concept,
                frequency=max(1, entry.isr.semantic_trace.__len__()),
                confidence=confidence,
                examples=[entry.entry_id],
                ambiguities=list(dict.fromkeys([*entry.ambiguities, *normalized["ambiguities"]])),
                relationships=list(entry.relationships),
                matched_entities=[entity for entity in entry.entities_identified if entity in normalized["entities"] or entity in normalized["expected_outputs"]],
                matched_constraints={key: value for key, value in pattern.constraints.items() if normalized["constraints"].get(key) == value},
                deterministic=True,
                prompt_used=False,
                modifies_runtime=False,
            )
            if not self.validator.validate(match):
                matches.append(match)
        matches = sorted(matches, key=lambda item: (-item.confidence, item.concept.concept_id))[: request.limit]
        return SemanticPatternRecognitionResult(
            count=len(matches),
            matches=matches,
            deterministic=True,
            prompt_used=False,
            modifies_runtime=False,
        )


class RecommendationScorer:
    def score(self, pattern: SemanticPatternMatch, regression_categories: list[str]) -> float:
        score = pattern.confidence * 0.7
        if pattern.concept.canonical_intent in {"write_patch", "repository_analysis"}:
            score += 0.1
        if regression_categories:
            score += 0.1
        if pattern.ambiguities:
            score += 0.05
        return round(min(score, 0.99), 2)


class RecommendationBuilder:
    def build(self, pattern: SemanticPatternMatch, *, confidence: float, regression_categories: list[str], patch_categories: list[str]) -> SemanticRecommendation:
        evidence = [
            SemanticEvidence(
                evidence_type="semantic_pattern_match",
                summary=f"Matched semantic pattern {pattern.pattern_id} with confidence {pattern.confidence}.",
                refs=[pattern.pattern_id, *pattern.examples],
            )
        ]
        if regression_categories:
            evidence.append(
                SemanticEvidence(
                    evidence_type="runtime_doctor_regression_context",
                    summary=f"Runtime Doctor categories observed: {', '.join(regression_categories)}.",
                    refs=regression_categories,
                )
            )
        if patch_categories:
            evidence.append(
                SemanticEvidence(
                    evidence_type="patch_knowledge_context",
                    summary=f"Patch knowledge categories related: {', '.join(patch_categories)}.",
                    refs=patch_categories,
                )
            )
        return SemanticRecommendation(
            related_concept=pattern.concept,
            justification=f"Recurring semantic concept {pattern.concept.canonical_intent} matched by canonical ISR structures and accumulated evidence.",
            expected_benefit="Improve future interpretation consistency by reviewing semantic examples, constraints, and ambiguity handling for this concept.",
            risks=["Recommendation is advisory only and must be validated by a human before changing runtime behavior."],
            candidate_modules=["services/semantic_runtime", "schemas/semantic_runtime"],
            estimated_impact="medium" if confidence < 0.85 else "high",
            confidence=confidence,
            evidence=evidence,
            status="pending_human_validation",
            modifies_semantic_interpreter=False,
            modifies_contract_compiler=False,
            modifies_governed_runtime=False,
            modifies_runtime_contracts=False,
            modifies_models=False,
        )


class RecommendationValidator:
    def validate(self, recommendation: SemanticRecommendation) -> list[str]:
        errors: list[str] = []
        if recommendation.status != "pending_human_validation":
            errors.append("semantic_recommendation_must_remain_pending_human_validation")
        if recommendation.modifies_semantic_interpreter:
            errors.append("semantic_recommendation_must_not_modify_semantic_interpreter")
        if recommendation.modifies_contract_compiler:
            errors.append("semantic_recommendation_must_not_modify_contract_compiler")
        if recommendation.modifies_governed_runtime:
            errors.append("semantic_recommendation_must_not_modify_governed_runtime")
        if recommendation.modifies_runtime_contracts:
            errors.append("semantic_recommendation_must_not_modify_runtime_contracts")
        if recommendation.modifies_models:
            errors.append("semantic_recommendation_must_not_modify_models")
        if not recommendation.evidence:
            errors.append("semantic_recommendation_requires_evidence")
        return errors


class RecommendationRepository:
    _recommendations: dict[str, SemanticRecommendation] = {}

    def add_many(self, recommendations: list[SemanticRecommendation]) -> None:
        for recommendation in recommendations:
            self._recommendations[recommendation.recommendation_id] = recommendation

    def list(self) -> list[SemanticRecommendation]:
        return sorted(self._recommendations.values(), key=lambda item: item.recommendation_id)

    def get(self, recommendation_id: str) -> SemanticRecommendation | None:
        return self._recommendations.get(recommendation_id)


class SemanticRecommendationEngine:
    def __init__(
        self,
        builder: RecommendationBuilder | None = None,
        scorer: RecommendationScorer | None = None,
        validator: RecommendationValidator | None = None,
        repository: RecommendationRepository | None = None,
    ) -> None:
        self.builder = builder or RecommendationBuilder()
        self.scorer = scorer or RecommendationScorer()
        self.validator = validator or RecommendationValidator()
        self.repository = repository or RecommendationRepository()

    def recommend(self, request: SemanticRecommendationRequest) -> SemanticRecommendationResult:
        regression_categories = self._regression_categories(request.doctor_report, request.regression_matrix)
        patch_categories = self._patch_categories(request.patch_knowledge_base)
        recommendations: list[SemanticRecommendation] = []
        for pattern in sorted(request.semantic_patterns, key=lambda item: (-item.confidence, item.pattern_id))[: request.limit]:
            confidence = self.scorer.score(pattern, regression_categories)
            recommendation = self.builder.build(pattern, confidence=confidence, regression_categories=regression_categories, patch_categories=patch_categories)
            if not self.validator.validate(recommendation):
                recommendations.append(recommendation)
        self.repository.add_many(recommendations)
        return SemanticRecommendationResult(
            count=len(recommendations),
            recommendations=recommendations,
            deterministic=True,
            read_only=True,
            side_effects=False,
            pending_human_validation=True,
        )

    def list(self) -> SemanticRecommendationResult:
        recommendations = self.repository.list()
        return SemanticRecommendationResult(count=len(recommendations), recommendations=recommendations)

    def get(self, recommendation_id: str) -> SemanticRecommendation | None:
        return self.repository.get(recommendation_id)

    def _regression_categories(self, report: dict[str, Any], matrix: dict[str, Any]) -> list[str]:
        categories: list[str] = []
        findings = report.get("findings", [])
        if isinstance(findings, list):
            categories.extend(str(item.get("category")) for item in findings if isinstance(item, dict) and item.get("category"))
        rows = matrix.get("rows", [])
        if isinstance(rows, list):
            categories.extend(str(item.get("category")) for item in rows if isinstance(item, dict) and item.get("status") in {"FAIL", "WARN"} and item.get("category"))
        return list(dict.fromkeys(categories))

    def _patch_categories(self, base: dict[str, Any]) -> list[str]:
        entries = base.get("entries", [])
        if not isinstance(entries, list):
            return []
        return list(dict.fromkeys(str(item.get("category")) for item in entries if isinstance(item, dict) and item.get("category")))


class SemanticCurriculumSerializer:
    def to_dict(self, curriculum: SemanticCurriculum) -> dict[str, Any]:
        return curriculum.model_dump(mode="json")

    def to_json(self, curriculum: SemanticCurriculum) -> str:
        return json.dumps(self.to_dict(curriculum), ensure_ascii=False, sort_keys=True)

    def from_dict(self, payload: dict[str, Any]) -> SemanticCurriculum:
        return SemanticCurriculum.model_validate(payload)

    def from_json(self, payload: str) -> SemanticCurriculum:
        return SemanticCurriculum.model_validate_json(payload)


class SemanticCurriculumRepository:
    _curriculum: SemanticCurriculum | None = None

    def __init__(self, knowledge: SemanticKnowledgeRepository | None = None, recommendation_repo: RecommendationRepository | None = None) -> None:
        self.knowledge = knowledge or SemanticKnowledgeRepository()
        self.recommendation_repo = recommendation_repo or RecommendationRepository()
        if SemanticCurriculumRepository._curriculum is None:
            SemanticCurriculumRepository._curriculum = self._build_initial()

    def get(self) -> SemanticCurriculum:
        assert SemanticCurriculumRepository._curriculum is not None
        return SemanticCurriculumRepository._curriculum

    def get_entry(self, entry_id: str) -> SemanticCurriculumEntry | None:
        for entry in self.get().entries:
            if entry.curriculum_entry_id == entry_id:
                return entry
        return None

    def review(self, request: SemanticCurriculumReviewRequest) -> SemanticCurriculum:
        curriculum = self.get()
        target = None
        for recommendation in self.recommendation_repo.list():
            if recommendation.recommendation_id == request.recommendation_id:
                target = recommendation
                break
        for entry in curriculum.entries:
            if target is not None and entry.concept.concept_id == target.related_concept.concept_id:
                if request.decision == "accepted":
                    entry.recommendations_accepted = list(dict.fromkeys([*entry.recommendations_accepted, request.recommendation_id]))
                else:
                    entry.recommendations_rejected = list(dict.fromkeys([*entry.recommendations_rejected, request.recommendation_id]))
        curriculum.evolutions.append(
            SemanticEvolution(
                changes=[f"review:{request.decision}:{request.recommendation_id}"],
                milestones=[
                    SemanticMilestone(
                        title="Semantic recommendation reviewed",
                        summary=request.rationale or f"Recommendation {request.recommendation_id} marked {request.decision}.",
                        evidence_refs=[request.recommendation_id],
                    )
                ],
            )
        )
        return curriculum

    def promote(self, request: SemanticCurriculumPromoteRequest) -> SemanticPromotionCandidate:
        entry = self.get_entry(request.curriculum_entry_id)
        if entry is None:
            raise KeyError("semantic_curriculum_entry_not_found")
        candidate = SemanticPromotionCandidate(
            competency=entry.competency,
            reason=request.reason,
            knowledge_used=entry.competency.knowledge_used,
            patterns_used=entry.learned_patterns,
            evidence=entry.evidence,
            regressions_related=entry.regressions_associated,
            expected_impact=request.expected_impact,
            risks=[*entry.competency.risks, "Promotion requires human approval before runtime incorporation."],
            rollback=["Do not include the promoted competency in the next Semantic Runtime version."],
            approval_required=True,
            status="candidate",
            auto_promoted=False,
            modifies_runtime=False,
        )
        curriculum = self.get()
        curriculum.promotion_candidates.append(candidate)
        curriculum.evolutions.append(
            SemanticEvolution(
                changes=[f"promotion_candidate_created:{candidate.promotion_candidate_id}"],
                milestones=[
                    SemanticMilestone(
                        title="Semantic promotion candidate created",
                        summary=request.reason,
                        evidence_refs=[candidate.promotion_candidate_id],
                    )
                ],
            )
        )
        return candidate

    def _build_initial(self) -> SemanticCurriculum:
        entries: list[SemanticCurriculumEntry] = []
        capabilities: list[SemanticCapability] = []
        for item in self.knowledge.list_entries():
            capability = SemanticCapability(
                capability_id=f"semantic_capability_{item.canonical_intent}",
                name=f"{item.concept.name} capability",
                description=f"Capability for recognizing and governing {item.canonical_intent}.",
                domain=item.scope,
            )
            competency = SemanticCompetency(
                competency_id=f"semantic_competency_{item.canonical_intent}",
                name=item.concept.name,
                description=item.concept.description,
                domain=item.scope,
                dependencies=[capability.capability_id],
                knowledge_used=[item.entry_id],
                risks=["Must not alter Semantic Runtime without human-approved version promotion."],
                firetests_related=[ref for evidence in item.evidence for ref in evidence.refs if "firetest" in ref],
            )
            entries.append(
                SemanticCurriculumEntry(
                    curriculum_entry_id=f"semantic_curriculum_{item.canonical_intent}",
                    concept=item.concept,
                    competency=competency,
                    learned_patterns=[pattern.pattern_id for pattern in item.patterns],
                    evidence=list(item.evidence),
                    regressions_associated=[],
                    firetests_related=competency.firetests_related,
                    maturity="LEARNING" if item.confidence != "high" else "STABLE",
                )
            )
            capabilities.append(capability)
        return SemanticCurriculum(
            entries=entries,
            capabilities=capabilities,
            evolutions=[
                SemanticEvolution(
                    changes=["curriculum_initialized_from_semantic_knowledge_base"],
                    milestones=[SemanticMilestone(title="Semantic Curriculum initialized", summary="Initial curriculum created from Semantic Knowledge Base.")],
                )
            ],
            auto_changes_runtime=False,
        )


class SemanticCurriculumService:
    def __init__(self, repository: SemanticCurriculumRepository | None = None) -> None:
        self.repository = repository or SemanticCurriculumRepository()

    def get(self) -> SemanticCurriculumResult:
        curriculum = self.repository.get()
        return SemanticCurriculumResult(
            curriculum=curriculum,
            report_markdown=self._markdown(curriculum),
            evolution_history=self._history(curriculum),
            read_only=True,
            side_effects=False,
        )

    def get_entry(self, entry_id: str) -> SemanticCurriculumEntry | None:
        return self.repository.get_entry(entry_id)

    def review(self, request: SemanticCurriculumReviewRequest) -> SemanticCurriculumResult:
        curriculum = self.repository.review(request)
        return SemanticCurriculumResult(curriculum=curriculum, report_markdown=self._markdown(curriculum), evolution_history=self._history(curriculum))

    def promote(self, request: SemanticCurriculumPromoteRequest) -> SemanticPromotionCandidate:
        return self.repository.promote(request)

    def _markdown(self, curriculum: SemanticCurriculum) -> str:
        lines = [
            "# Semantic Curriculum Report",
            "",
            f"- curriculum_id: {curriculum.curriculum_id}",
            f"- version: {curriculum.version.version}",
            f"- entries: {len(curriculum.entries)}",
            f"- promotion_candidates: {len(curriculum.promotion_candidates)}",
            f"- auto_changes_runtime: {curriculum.auto_changes_runtime}",
            "",
            "## Entries",
        ]
        for entry in curriculum.entries:
            lines.append(f"- {entry.curriculum_entry_id}: {entry.concept.canonical_intent} ({entry.maturity})")
        return "\n".join(lines)

    def _history(self, curriculum: SemanticCurriculum) -> dict[str, Any]:
        return {
            "semantic_evolution_history": [evolution.model_dump(mode="json") for evolution in curriculum.evolutions],
            "promotion_candidates": [candidate.model_dump(mode="json") for candidate in curriculum.promotion_candidates],
        }
