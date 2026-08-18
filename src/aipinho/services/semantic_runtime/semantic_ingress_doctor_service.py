from __future__ import annotations

import unicodedata
from typing import Any

from aipinho.schemas.governance.lifecycle import CanonicalIntentDecision
from aipinho.schemas.intent.semantic_intent_graph import SemanticIntentGraph
from aipinho.schemas.semantic_runtime.semantic_ingress import (
    IntentCandidate,
    IntentDecision,
    OperationContractCandidate,
    OperationContractDecision,
    PromptNormalization,
    SemanticIngressDoctorReport,
    SemanticProposition,
    StateEffect,
)
from aipinho.services.governance.intent.canonical_intent_router import CanonicalIntentRouter
from aipinho.services.governance.intent.intent_normalizer import normalize_text
from aipinho.services.semantic_runtime.semantic_proposition_normalization_service import SemanticPropositionNormalizationService


class SemanticIngressDoctorService:
    """Read-only explanation of prompt ingress before operation contracts.

    The service observes the same canonical semantic components used by the
    Runtime, then serializes the intermediate reasoning. It does not promote,
    override, or mutate Runtime decisions.
    """

    _MOJIBAKE_MARKERS = ("Ã", "Â", "â", "�", "ï¿½")
    _CONTROL_TRANSFORMATION = "control_chars_removed"
    _NFKD_TRANSFORMATION = "unicode_nfkd"
    _CASEFOLD_TRANSFORMATION = "casefold"
    _WHITESPACE_TRANSFORMATION = "whitespace_collapsed"

    def __init__(
        self,
        *,
        semantic_normalizer: SemanticPropositionNormalizationService | None = None,
        router: CanonicalIntentRouter | None = None,
    ) -> None:
        self.semantic_normalizer = semantic_normalizer or SemanticPropositionNormalizationService()
        self.router = router or CanonicalIntentRouter(semantic_normalizer=self.semantic_normalizer)

    def analyze(
        self,
        prompt: str,
        *,
        source_channel: str = "unknown",
        actual_intent: dict[str, Any] | CanonicalIntentDecision | None = None,
        actual_operation_contract: dict[str, Any] | None = None,
    ) -> SemanticIngressDoctorReport:
        normalization = self._normalize_prompt(prompt)
        semantic_graph = self.semantic_normalizer.normalize(prompt)
        routed_intent = self._coerce_intent(actual_intent) or self.router.decide(prompt, source_channel=source_channel)
        propositions = self._propositions(semantic_graph, normalization)
        state_effects = self._state_effects(semantic_graph)
        intent_decision = self._intent_decision(routed_intent, semantic_graph, propositions)
        operation_decision = self._operation_contract_decision(
            intent=routed_intent,
            semantic_graph=semantic_graph,
            intent_candidates=intent_decision.candidates,
            actual_operation_contract=actual_operation_contract,
        )
        reason_codes = self._reason_codes(normalization, semantic_graph, intent_decision, operation_decision)
        status = "invalid" if "PROMPT_MISSING" in reason_codes else "partial" if reason_codes else "complete"
        warnings = [code for code in reason_codes if code.startswith("ENCODING_") or code.endswith("_AMBIGUITY")]
        return SemanticIngressDoctorReport(
            status=status,  # type: ignore[arg-type]
            prompt_normalization=normalization,
            semantic_propositions=propositions,
            state_effects=state_effects,
            intent_decision=intent_decision,
            operation_contract_decision=operation_decision,
            reason_codes=reason_codes,
            warnings=warnings,
            trace=[
                {"stage": "PromptNormalization", "status": normalization.encoding_issues or "ok"},
                {"stage": "SemanticPropositionExtraction", "count": len(propositions)},
                {"stage": "StateEffectResolution", "state_effect": semantic_graph.state_effect},
                {"stage": "IntentArbitration", "selected": routed_intent.intent_type},
                {"stage": "OperationContractSelection", "selected": operation_decision.selected_contract_type},
            ],
        )

    def _normalize_prompt(self, prompt: str) -> PromptNormalization:
        original = str(prompt or "")
        issues: list[str] = []
        transformations = [
            self._NFKD_TRANSFORMATION,
            self._CASEFOLD_TRANSFORMATION,
            self._WHITESPACE_TRANSFORMATION,
        ]
        if any(unicodedata.category(ch)[0] == "C" and ch not in {"\n", "\r", "\t"} for ch in original):
            transformations.append(self._CONTROL_TRANSFORMATION)
            issues.append("control_chars_present")
        if any(marker in original for marker in self._MOJIBAKE_MARKERS):
            issues.append("mojibake_suspected")
        variants = self._diagnostic_variants(original)
        confidence = 1.0
        if issues:
            confidence = 0.65 if "mojibake_suspected" in issues else 0.85
        return PromptNormalization(
            original_text=original,
            normalized_text=normalize_text(original),
            encoding_detected="unicode_text_with_possible_mojibake" if "mojibake_suspected" in issues else "unicode_text",
            encoding_issues=issues,
            transformations=list(dict.fromkeys(transformations)),
            text_variants=variants,
            confidence=confidence,
        )

    def _diagnostic_variants(self, text: str) -> dict[str, str]:
        variants: dict[str, str] = {}
        try:
            decoded = text.encode("latin1").decode("utf-8")
        except UnicodeError:
            decoded = ""
        if decoded and decoded != text:
            variants["latin1_to_utf8"] = normalize_text(decoded)
        return variants

    def _propositions(self, graph: SemanticIntentGraph, normalization: PromptNormalization) -> list[SemanticProposition]:
        propositions: list[SemanticProposition] = []
        if normalization.original_text.strip():
            propositions.append(
                SemanticProposition(
                    proposition_type="objective",
                    subject="operator",
                    predicate="submitted_prompt",
                    object_value={"prompt_chars": len(normalization.original_text)},
                    confidence=normalization.confidence,
                    evidence_refs=["prompt:original_text"],
                )
            )
        for effect in graph.requested_effects:
            propositions.append(
                SemanticProposition(
                    proposition_type="effect_expected",
                    subject="state",
                    predicate="requests",
                    object_value=effect,
                    polarity="positive",
                    confidence=1.0,
                    evidence_refs=[f"semantic_graph:requested_effect:{effect}"],
                )
            )
        for effect in graph.prohibited_effects:
            propositions.append(
                SemanticProposition(
                    proposition_type="restriction",
                    subject="state",
                    predicate="prohibits",
                    object_value=effect,
                    polarity="negative",
                    confidence=1.0,
                    evidence_refs=[f"semantic_graph:prohibited_effect:{effect}"],
                )
            )
        for name in (
            "observational_intent",
            "planning_intent",
            "mutation_intent",
            "execution_intent",
            "approval_intent",
            "knowledge_output",
            "artifact_output",
            "readonly_contract",
        ):
            if bool(getattr(graph, name, False)):
                propositions.append(
                    SemanticProposition(
                        proposition_type="intent_signal",
                        subject="semantic_graph",
                        predicate=name,
                        object_value=True,
                        confidence=1.0,
                        evidence_refs=[f"semantic_graph:{name}"],
                    )
                )
        return propositions

    def _state_effects(self, graph: SemanticIntentGraph) -> list[StateEffect]:
        effects = [
            StateEffect(
                target="workspace",
                effect=self._workspace_level(graph.workspace_effect),
                confidence=1.0,
                evidence_refs=["semantic_graph:workspace_effect", *self._effect_refs(graph)],
            ),
            StateEffect(
                target="filesystem",
                effect=self._filesystem_level(graph.filesystem_effect),
                confidence=1.0,
                evidence_refs=["semantic_graph:filesystem_effect", *self._effect_refs(graph)],
            ),
            StateEffect(
                target="runtime",
                effect=self._runtime_level(graph.runtime_effect),
                confidence=1.0,
                evidence_refs=["semantic_graph:runtime_effect", *self._effect_refs(graph)],
            ),
            StateEffect(
                target="knowledge",
                effect="read_only" if graph.knowledge_output or graph.observational_intent else "none",
                confidence=1.0,
                evidence_refs=["semantic_graph:knowledge_output", "semantic_graph:observational_intent"],
            ),
        ]
        return effects

    def _intent_decision(
        self,
        selected: CanonicalIntentDecision,
        graph: SemanticIntentGraph,
        propositions: list[SemanticProposition],
    ) -> IntentDecision:
        support_by_type = {
            proposition.proposition_type: proposition.proposition_id for proposition in propositions
        }
        candidates = [
            self._candidate("workspace_analysis_readonly", "workspace_analysis_readonly", graph.observational_intent or graph.knowledge_output, graph.readonly_contract, support_by_type),
            self._candidate("product_planning_readonly", "product_planning_readonly", graph.planning_intent, graph.readonly_contract, support_by_type),
            self._candidate("proposal_only", "patch_preview", graph.state_effect == "proposal_only", not graph.readonly_contract, support_by_type),
            self._candidate("patch_or_write_request", "patch_request", graph.mutation_intent and graph.state_effect == "workspace_mutation", not graph.readonly_contract, support_by_type),
            self._candidate("governed_shell_request", "run_command", graph.execution_intent and graph.state_effect in {"runtime_execution", "build_execution"}, not graph.readonly_contract, support_by_type),
            self._candidate("approval_command", "approval_command", graph.approval_intent, True, support_by_type),
            self._candidate("conversation", "conversation", graph.state_effect == "none", True, support_by_type),
        ]
        for index, candidate in enumerate(candidates):
            if candidate.intent_id == selected.intent_type or candidate.operation_type == selected.operation_type:
                candidates[index] = candidate.model_copy(update={"rejected_reason": None, "arbitration_score": max(candidate.arbitration_score, selected.confidence)})
        criteria = [
            "selected_by_existing_canonical_intent_router",
            "state_effect_observed_not_overridden",
            "readonly_constraints_preserved_when_selected",
        ]
        reason_codes = []
        if graph.readonly_contract and selected.operation_type not in {"workspace_analysis_readonly", "product_planning_readonly", "conversation", "capability_truth", "workspace_permission_list"}:
            reason_codes.append("STATE_EFFECT_CONTRACT_MISMATCH")
        if len([item for item in candidates if item.arbitration_score >= 0.5]) > 1:
            reason_codes.append("INTENT_AMBIGUITY")
        return IntentDecision(
            selected_intent_id=selected.intent_type,
            selected_operation_type=selected.operation_type,
            candidates=candidates,
            criteria=criteria,
            evidence_refs=list(dict.fromkeys([*selected.evidence, *graph.evidence])),
            confidence=selected.confidence,
            reason_codes=reason_codes,
        )

    def _candidate(
        self,
        intent_id: str,
        operation_type: str,
        active: bool,
        compatible: bool,
        support_by_type: dict[str, str],
    ) -> IntentCandidate:
        score = 0.0
        refs: list[str] = []
        if active:
            score += 0.7
            refs.extend(support_by_type.values())
        if compatible:
            score += 0.3
        rejected = None if active and compatible else "semantic_evidence_or_state_effect_insufficient"
        return IntentCandidate(
            intent_id=intent_id,
            operation_type=operation_type,
            confidence=round(min(score, 1.0), 4),
            supporting_propositions=list(dict.fromkeys(refs)),
            rejected_reason=rejected,
            arbitration_score=round(min(score, 1.0), 4),
        )

    def _operation_contract_decision(
        self,
        *,
        intent: CanonicalIntentDecision,
        semantic_graph: SemanticIntentGraph,
        intent_candidates: list[IntentCandidate],
        actual_operation_contract: dict[str, Any] | None,
    ) -> OperationContractDecision:
        selected_contract = str(
            (actual_operation_contract or {}).get("contract_type")
            or self._contract_for_operation(intent.operation_type)
        )
        selected_operation = str((actual_operation_contract or {}).get("operation_type") or intent.operation_type)
        candidates = [
            OperationContractCandidate(
                contract_type=self._contract_for_operation(candidate.operation_type),
                operation_type=candidate.operation_type,
                confidence=candidate.confidence,
                state_effect_alignment=self._contract_alignment(candidate.operation_type, semantic_graph),
                supporting_intent=candidate.intent_id,
                rejected_reason=candidate.rejected_reason,
                evidence_refs=[f"intent_candidate:{candidate.intent_id}"],
            )
            for candidate in intent_candidates
        ]
        alignment = self._contract_alignment(selected_operation, semantic_graph)
        reason_codes = []
        if alignment == "conflict":
            reason_codes.append("OPERATION_CONTRACT_STATE_EFFECT_MISMATCH")
        if semantic_graph.readonly_contract and selected_contract in {"filesystem_write", "patch_request", "project_generation"}:
            reason_codes.append("READONLY_CONTRACT_PROMOTED_TO_MUTATION")
        return OperationContractDecision(
            selected_contract_type=selected_contract,
            selected_operation_type=selected_operation,
            candidates=candidates,
            relation_to_intent="selected_contract_derived_from_existing_intent_decision",
            relation_to_state_effects=alignment,
            evidence_refs=["actual_operation_contract" if actual_operation_contract else "canonical_intent_router"],
            confidence=1.0 if alignment != "conflict" else 0.45,
            reason_codes=reason_codes,
        )

    def _reason_codes(
        self,
        normalization: PromptNormalization,
        graph: SemanticIntentGraph,
        intent: IntentDecision,
        operation: OperationContractDecision,
    ) -> list[str]:
        reasons: list[str] = []
        if not normalization.original_text.strip():
            reasons.append("PROMPT_MISSING")
        if "mojibake_suspected" in normalization.encoding_issues:
            reasons.append("ENCODING_MOJIBAKE_SUSPECTED")
        if graph.state_effect == "none" and not (graph.observational_intent or graph.planning_intent or graph.knowledge_output):
            reasons.append("STATE_EFFECT_UNRESOLVED")
        reasons.extend(intent.reason_codes)
        reasons.extend(operation.reason_codes)
        return list(dict.fromkeys(reasons))

    def _coerce_intent(self, value: dict[str, Any] | CanonicalIntentDecision | None) -> CanonicalIntentDecision | None:
        if value is None:
            return None
        if isinstance(value, CanonicalIntentDecision):
            return value
        if isinstance(value, dict):
            data = dict(value)
            graph = data.get("semantic_intent_graph")
            if isinstance(graph, dict):
                data["semantic_intent_graph"] = SemanticIntentGraph(**graph)
            fields = getattr(CanonicalIntentDecision, "model_fields", None) or getattr(CanonicalIntentDecision, "__fields__", {})
            return CanonicalIntentDecision(**{key: val for key, val in data.items() if key in fields})
        return None

    def _contract_for_operation(self, operation_type: str) -> str:
        if operation_type in {"workspace_analysis_readonly", "readonly_analysis", "product_planning_readonly"}:
            return "analysis_readonly"
        if operation_type in {"patch_request", "patch_apply", "patch_preview"}:
            return "patch_request"
        if operation_type in {"project_generation", "project_bootstrap"}:
            return "project_generation"
        if operation_type in {"run_command", "governed_shell_request"}:
            return "shell_build_test"
        if operation_type in {"filesystem_write", "filesystem_create_directory"}:
            return "filesystem_write"
        return operation_type or "conversation"

    def _contract_alignment(self, operation_type: str, graph: SemanticIntentGraph) -> str:
        mutation_ops = {"patch_request", "patch_apply", "project_generation", "project_bootstrap", "filesystem_write", "filesystem_create_directory"}
        execution_ops = {"run_command", "governed_shell_request"}
        readonly_ops = {"workspace_analysis_readonly", "readonly_analysis", "product_planning_readonly", "conversation", "capability_truth", "workspace_permission_list"}
        if graph.readonly_contract and operation_type in mutation_ops | execution_ops:
            return "conflict"
        if graph.state_effect == "workspace_mutation" and operation_type in mutation_ops:
            return "aligned"
        if graph.state_effect in {"runtime_execution", "build_execution"} and operation_type in execution_ops:
            return "aligned"
        if graph.state_effect in {"knowledge_only", "planning_only", "none"} and operation_type in readonly_ops:
            return "aligned"
        if graph.state_effect == "proposal_only" and operation_type in {"patch_preview", "patch_request"}:
            return "partial"
        return "partial"

    def _workspace_level(self, effect: str) -> str:
        return {
            "immutable": "immutable",
            "knowledge_only": "read_only",
            "planning_only": "read_only",
            "proposal_only": "temporary",
            "mutable": "mutable",
        }.get(effect, "none")

    def _filesystem_level(self, effect: str) -> str:
        return {
            "prohibited": "prohibited",
            "knowledge_only": "read_only",
            "proposal_only": "temporary",
            "mutable": "mutable",
        }.get(effect, "none")

    def _runtime_level(self, effect: str) -> str:
        return {
            "prohibited": "prohibited",
            "build_execution": "mutable",
            "command_execution": "mutable",
        }.get(effect, "none")

    def _effect_refs(self, graph: SemanticIntentGraph) -> list[str]:
        refs = [f"semantic_graph:evidence:{item}" for item in graph.evidence]
        return refs[:12]
