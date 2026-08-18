from __future__ import annotations

from uuid import uuid4

from aipinho.schemas.intent.intent_evidence import IntentEvidence
from aipinho.schemas.intent.intent_map import IntentMap
from aipinho.schemas.intent.prompt_analysis_request import PromptAnalysisRequest
from aipinho.schemas.intent.prompt_analysis_response import PromptAnalysisResponse, PromptContractPreviewResponse
from aipinho.schemas.intent.workspace_resolution import WorkspaceResolution
from aipinho.schemas.policy.policy_decision import PolicyResolveRequest, RoleInput, UserConstraints, WorkspaceInput
from aipinho.schemas.tasks.task_contract import TaskContractInput
from aipinho.services.governance.policy.effective_policy_decision_service import EffectivePolicyDecisionService
from aipinho.services.prompt_intelligence.ambiguity_detector import AmbiguityDetector
from aipinho.services.prompt_intelligence.concept_matcher import ConceptMatcher
from aipinho.services.prompt_intelligence.intent_classifier import IntentClassifier
from aipinho.services.prompt_intelligence.intent_trace_builder import IntentTraceBuilder
from aipinho.services.prompt_intelligence.output_intent_detector import OutputIntentDetector
from aipinho.services.prompt_intelligence.prompt_segmenter import PromptSegmenter
from aipinho.services.prompt_intelligence.risk_classifier import RiskClassifier
from aipinho.services.prompt_intelligence.self_reference_detector import SelfReferenceDetector
from aipinho.services.prompt_intelligence.workspace_resolver import WorkspaceResolver
from aipinho.services.prompt_intelligence.report_deliverable_extractor_service import (
    ReportDeliverableExtractorService,
)
from aipinho.services.prompt_intelligence.workspace_reference_extractor_service import (
    WorkspaceReferenceExtractorService,
)
from aipinho.services.prompt_intelligence.canonical_operation_service import CanonicalOperationService
from aipinho.services.semantic_runtime.semantic_proposition_normalization_service import SemanticPropositionNormalizationService


class PromptIntelligenceService:
    def __init__(self) -> None:
        self.concept_matcher = ConceptMatcher().load()
        self.segmenter = PromptSegmenter(self.concept_matcher)
        self.self_reference_detector = SelfReferenceDetector(self.concept_matcher)
        self.output_detector = OutputIntentDetector(self.concept_matcher)
        self.workspace_resolver = WorkspaceResolver(self.concept_matcher)
        self.workspace_reference_extractor = WorkspaceReferenceExtractorService()
        self.deliverable_extractor = ReportDeliverableExtractorService()
        self.intent_classifier = IntentClassifier(concept_matcher=self.concept_matcher).load()
        self.ambiguity_detector = AmbiguityDetector(concept_matcher=self.concept_matcher).load()
        self.risk_classifier = RiskClassifier().load()
        self.trace_builder = IntentTraceBuilder()
        self.canonical_operations = CanonicalOperationService()
        self.policy_decisions = EffectivePolicyDecisionService()
        self.semantic_propositions = SemanticPropositionNormalizationService(
            concept_matcher=self.concept_matcher,
            output_detector=self.output_detector,
        )

    def analyze(self, request: PromptAnalysisRequest) -> PromptAnalysisResponse:
        normalized = self.concept_matcher.normalize(request.prompt)
        matches = self.concept_matcher.match(request.prompt)
        segments = self.segmenter.segment(request.prompt)
        self_reference_pre = any(match.concept_id == "self_actor" for match in matches)
        workspace_pre = self.workspace_resolver.resolve(request.prompt, matches, self_reference=False)
        self_reference = self.self_reference_detector.is_self_reference(matches, workspace_declared=workspace_pre.declared)
        workspace = self.workspace_resolver.resolve(request.prompt, matches, self_reference=self_reference)
        context_workspace = self._context_workspace_resolution(request.context)
        if not self_reference and not workspace.path and context_workspace is not None:
            workspace = context_workspace
        workspace_references = self.workspace_reference_extractor.extract(request.prompt)
        requested_deliverables = self.deliverable_extractor.extract(request.prompt)
        output_intent = self.output_detector.detect(request.prompt, matches)
        semantic_graph = self.semantic_propositions.normalize(
            request.prompt,
            matches=matches,
            output_intent=output_intent,
        )
        classification = self.intent_classifier.classify(
            request.prompt,
            matches,
            self_reference=self_reference,
            workspace=workspace,
            output_intent=output_intent,
            semantic_graph=semantic_graph,
        )
        is_operational = classification.requires_task or classification.intent_type in {"patch_request", "artifact_generation", "readonly_analysis", "validation_request"}
        ambiguity = self.ambiguity_detector.detect(
            request.prompt,
            matches,
            workspace_requires_clarification=workspace.requires_clarification or (classification.requires_workspace and not workspace.declared),
            workspace_resolved=bool(workspace.declared and workspace.path),
            confidence=classification.confidence,
            is_operational=is_operational,
        )
        risk = self.risk_classifier.classify(
            intent_type=classification.intent_type,
            actions=classification.requested_actions,
            protected_workspace=workspace.protected,
            ambiguous=ambiguity.is_ambiguous,
        )
        target = self.workspace_resolver.target_for(workspace, self_reference=self_reference)
        evidence = [
            IntentEvidence(kind=match.concept_type, value=match.concept_id, confidence=match.confidence, source="config/policies/concept_registry.yaml")
            for match in matches
        ]
        trace = [
            self.trace_builder.item(
                stage="prompt_normalization",
                rule="configurable_text_normalization",
                decision="computed",
                reason="prompt_normalized_for_concept_matching",
                source="services/prompt_intelligence/concept_matcher.py",
                input={"normalized_prompt": normalized},
            ),
            self.trace_builder.item(
                stage="concept_matching",
                rule="concept_registry_aliases",
                decision="computed",
                reason="concept_aliases_matched_from_config",
                source="config/policies/concept_registry.yaml",
                input={"matches": [match.concept_id for match in matches]},
            ),
            self.trace_builder.item(
                stage="semantic_proposition_normalization",
                rule="state_effect_principle",
                decision=semantic_graph.state_effect,
                reason="semantic_propositions_normalized_before_intent_mapping",
                source="services/semantic_runtime/semantic_proposition_normalization_service.py",
                input={
                    "readonly_contract": semantic_graph.readonly_contract,
                    "requested_effects": semantic_graph.requested_effects,
                    "prohibited_effects": semantic_graph.prohibited_effects,
                },
            ),
            self.trace_builder.item(
                stage="intent_classification",
                rule="intent_taxonomy",
                decision=classification.intent_type,
                reason="intent_classified_from_concepts_and_target",
                source="config/policies/intent_taxonomy.yaml",
                input={"intent_type": classification.intent_type, "task_type": classification.task_type},
            ),
        ]
        warnings: list[str] = []
        requires_workspace = classification.requires_workspace
        if classification.intent_type in {"self_analysis", "capability_explanation", "in_chat_final_report", "conversation"}:
            requires_workspace = False
        if ambiguity.requires_clarification:
            warnings.append("requires_clarification")
        if workspace.protected:
            warnings.append("protected_workspace_detected")
        intent_map = IntentMap(
            intent_id=f"intent_{uuid4().hex}",
            raw_prompt=request.prompt,
            normalized_prompt=normalized,
            language="pt-BR",
            intent_type=classification.intent_type,
            task_type=classification.task_type,
            requires_task=classification.requires_task,
            requires_workspace=requires_workspace,
            requires_approval=classification.requires_approval,
            requested_actions=[] if ambiguity.requires_clarification and classification.intent_type == "unknown" else classification.requested_actions,
            actor=classification.actor,
            operation=classification.operation,
            object=classification.object,
            target=target,
            output_intent=output_intent,
            workspace=workspace,
            risk=risk,
            ambiguity=ambiguity,
            confidence=classification.confidence,
            evidence=evidence,
            warnings=warnings,
            trace=trace,
            segments=segments,
            workspace_references=workspace_references,
            requested_deliverables=requested_deliverables,
            semantic_intent_graph=semantic_graph,
        )
        intent_map.operation_type = self.canonical_operations.from_intent(intent_map)  # type: ignore[assignment]
        return PromptAnalysisResponse(intent_map=intent_map, warnings=warnings, trace=trace)

    def _context_workspace_resolution(self, context: dict[str, object]) -> WorkspaceResolution | None:
        for key in ("active_workspace", "workspace", "workspace_path", "workspace_ref"):
            value = context.get(key)
            if isinstance(value, str) and value.strip():
                path = value.strip()
                policy = self.workspace_resolver.workspace_policy.evaluate(workspace_path=path, requires_workspace=True)
                return WorkspaceResolution(
                    path=path,
                    declared=True,
                    protected=policy.blocked,
                    requires_clarification=False,
                    reason=f"context_{policy.reason}",
                )
        return None

    def to_policy_request(self, intent_map: IntentMap) -> PolicyResolveRequest:
        task_type = "conversation" if intent_map.task_type == "none" else intent_map.task_type
        return PolicyResolveRequest(
            request_id=intent_map.intent_id,
            intent=intent_map.to_policy_intent_summary(),
            task=TaskContractInput(
                task_type=task_type,  # type: ignore[arg-type]
                operation_type=intent_map.operation_type,
                intent_type=intent_map.intent_type,
                workspace_ref=intent_map.workspace.path,
                requested_actions=intent_map.requested_actions,
                read_only=intent_map.semantic_intent_graph.readonly_contract or intent_map.intent_type in {"conversation", "self_analysis", "capability_explanation", "in_chat_final_report", "readonly_analysis", "rag_query"},
                approval_requested=False,
            ),
            workspace=WorkspaceInput(path=intent_map.workspace.path, declared=intent_map.workspace.declared),
            role=RoleInput(role_id="artifact_writer" if intent_map.intent_type == "artifact_generation" else "executor" if intent_map.requires_task else "planner"),
            user_constraints=UserConstraints(read_only=intent_map.semantic_intent_graph.readonly_contract or intent_map.intent_type == "readonly_analysis"),
        )

    def contract_preview(self, request: PromptAnalysisRequest) -> PromptContractPreviewResponse:
        analysis = self.analyze(request)
        warnings = list(analysis.warnings)
        try:
            policy_request = self.to_policy_request(analysis.intent_map)
            preview_model = self.policy_decisions.contract_preview_for_policy_request(policy_request)
            preview = preview_model.model_dump() if hasattr(preview_model, 'model_dump') else preview_model.dict()
        except Exception as exc:
            warnings.append("dependency_unavailable")
            preview = {"status": "degraded", "error": str(exc)}
        return PromptContractPreviewResponse(intent_map=analysis.intent_map, policy_preview=preview, warnings=warnings)

    def status(self) -> dict[str, object]:
        return {
            "status": "ok",
            "concept_registry": self.concept_matcher.status(),
            "intent_taxonomy": self.intent_classifier.status(),
            "risk_policy": self.risk_classifier.status(),
            "service": "prompt_intelligence",
            "canonical_operations": self.canonical_operations.status(),
            "execution_enabled": True,
        }
