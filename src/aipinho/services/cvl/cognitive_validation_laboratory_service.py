from __future__ import annotations

from pathlib import Path
from typing import Any

from aipinho.core.paths import PATHS
from aipinho.schemas.cvl import (
    CognitiveValidationLaboratoryResult,
    CoverageMetric,
    CoverageReport,
    DependencyGraph,
    DependencyImpactReport,
    DependencyNode,
    FireTestProfile,
    FireTestSuite,
    PredictedFailure,
    PredictedSuccess,
    PredictionReport,
    SimulationRequest,
    SimulationResult,
    SimulationStep,
)


class FireTestLaboratoryService:
    """Read-only profile registry for cognitive validation scenarios."""

    def suite(self, profiles: list[FireTestProfile], *, name: str = "cognitive_validation_suite") -> FireTestSuite:
        seen: set[str] = set()
        rows: list[FireTestProfile] = []
        for profile in profiles:
            if profile.profile_id in seen:
                raise ValueError("duplicate_firetest_profile_id")
            seen.add(profile.profile_id)
            rows.append(profile)
        return FireTestSuite(name=name, profiles=rows)

    def get_profile(self, suite: FireTestSuite, profile_id: str) -> FireTestProfile | None:
        return next((profile for profile in suite.profiles if profile.profile_id == profile_id), None)


class CognitiveDependencyGraphService:
    """Builds a static dependency graph from declared cognitive contracts."""

    def build(self, profile: FireTestProfile) -> DependencyGraph:
        nodes: dict[str, DependencyNode] = {}
        edges: list[dict[str, str]] = []

        previous_pipeline_node: str | None = None
        for index, stage in enumerate(profile.expected_pipeline):
            node_id = self._node_id("pipeline", stage)
            nodes[node_id] = DependencyNode(
                node_id=node_id,
                node_type="pipeline",
                label=stage,
                depends_on=[previous_pipeline_node] if previous_pipeline_node else [],
                impact="pipeline_progression",
                criticality="high" if index == 0 else "medium",
            )
            if previous_pipeline_node:
                edges.append({"from": previous_pipeline_node, "to": node_id})
            previous_pipeline_node = node_id

        anchor = self._node_id("pipeline", profile.expected_pipeline[0]) if profile.expected_pipeline else None
        for contract in profile.involved_contracts:
            node_id = self._node_id("contract", contract)
            nodes[node_id] = DependencyNode(
                node_id=node_id,
                node_type="contract",
                label=contract,
                dependents=[anchor] if anchor else [],
                impact="contract_satisfaction",
                criticality="high",
            )
            if anchor:
                nodes[anchor].depends_on.append(node_id)
                edges.append({"from": node_id, "to": anchor})

        for module in profile.involved_modules:
            node_id = self._node_id("module", module)
            nodes[node_id] = DependencyNode(
                node_id=node_id,
                node_type="module",
                label=module,
                impact="implementation_support",
                criticality="medium",
            )

        for capability in profile.expected_capabilities:
            node_id = self._node_id("capability", capability)
            target = self._capability_target(profile.expected_pipeline)
            nodes[node_id] = DependencyNode(
                node_id=node_id,
                node_type="capability",
                label=capability,
                dependents=[target] if target else [],
                impact="knowledge_or_observation_required",
                criticality="high",
            )
            if target and target in nodes:
                nodes[target].depends_on.append(node_id)
                edges.append({"from": node_id, "to": target})

        for artifact in profile.expected_artifacts:
            node_id = self._node_id("artifact", artifact)
            source = self._artifact_source(profile.expected_pipeline)
            nodes[node_id] = DependencyNode(
                node_id=node_id,
                node_type="artifact",
                label=artifact,
                depends_on=[source] if source else [],
                impact="evidence_materialization",
                criticality="high",
            )
            if source and source in nodes:
                nodes[source].dependents.append(node_id)
                edges.append({"from": source, "to": node_id})

        self._normalize_dependents(nodes, edges)
        return DependencyGraph(source_profile_id=profile.profile_id, nodes=list(nodes.values()), edges=edges)

    def impact(self, graph: DependencyGraph, source_node_id: str) -> DependencyImpactReport:
        node_ids = {node.node_id for node in graph.nodes}
        if source_node_id not in node_ids:
            return DependencyImpactReport(
                source_node_id=source_node_id,
                impact_summary="Source node is not present in the dependency graph.",
                criticality="low",
            )
        direct = sorted({edge["to"] for edge in graph.edges if edge.get("from") == source_node_id})
        transitive = self._transitive_dependents(graph, direct)
        impacted = list(dict.fromkeys([*direct, *transitive]))
        return DependencyImpactReport(
            source_node_id=source_node_id,
            impacted_node_ids=impacted,
            direct_dependents=direct,
            transitive_dependents=transitive,
            impact_summary=f"{len(impacted)} node(s) depend on {source_node_id}.",
            criticality="high" if len(impacted) > 3 else "medium" if impacted else "low",
        )

    def _capability_target(self, stages: list[str]) -> str | None:
        for token in ("capability", "perception", "validation", "artifact"):
            for stage in stages:
                if token in stage.casefold():
                    return self._node_id("pipeline", stage)
        return self._node_id("pipeline", stages[0]) if stages else None

    def _artifact_source(self, stages: list[str]) -> str | None:
        for token in ("artifact", "renderer", "validation"):
            for stage in stages:
                if token in stage.casefold():
                    return self._node_id("pipeline", stage)
        return self._node_id("pipeline", stages[-1]) if stages else None

    def _normalize_dependents(self, nodes: dict[str, DependencyNode], edges: list[dict[str, str]]) -> None:
        dependents: dict[str, list[str]] = {}
        for edge in edges:
            dependents.setdefault(edge["from"], []).append(edge["to"])
        for node_id, node in nodes.items():
            merged = list(dict.fromkeys([*node.dependents, *dependents.get(node_id, [])]))
            nodes[node_id] = node.model_copy(update={"depends_on": list(dict.fromkeys(node.depends_on)), "dependents": merged})

    def _transitive_dependents(self, graph: DependencyGraph, initial: list[str]) -> list[str]:
        edges_by_source: dict[str, list[str]] = {}
        for edge in graph.edges:
            edges_by_source.setdefault(edge["from"], []).append(edge["to"])
        visited: set[str] = set()
        stack = list(initial)
        while stack:
            node = stack.pop(0)
            for child in edges_by_source.get(node, []):
                if child in visited:
                    continue
                visited.add(child)
                stack.append(child)
        return sorted(visited - set(initial))

    def _node_id(self, node_type: str, label: str) -> str:
        normalized = "".join(ch if ch.isalnum() else "_" for ch in label.casefold()).strip("_")
        return f"{node_type}:{normalized or 'unnamed'}"


class CognitiveGapPredictor:
    """Predicts likely blocking boundaries without invoking the Runtime."""

    def predict(
        self,
        profile: FireTestProfile,
        *,
        graph: DependencyGraph | None = None,
        available_capabilities: list[str] | None = None,
    ) -> PredictionReport:
        early_prediction = self._predict_semantic_ingress(profile, graph=graph)
        if early_prediction is not None:
            return early_prediction
        boundary_prediction = self._predict_workspace_role_boundary(profile, graph=graph)
        if boundary_prediction is not None:
            return boundary_prediction
        project_analysis_prediction = self._predict_project_analysis_frontier(profile, graph=graph)
        if project_analysis_prediction is not None:
            return project_analysis_prediction
        public_boundary_prediction = self._predict_public_runtime_boundary(profile, graph=graph)
        if public_boundary_prediction is not None:
            return public_boundary_prediction
        media_inventory_prediction = self._predict_media_inventory_sufficiency_frontier(profile, graph=graph)
        if media_inventory_prediction is not None:
            return media_inventory_prediction
        observational_binding_prediction = self._predict_observational_binding_frontier(profile, graph=graph)
        if observational_binding_prediction is not None:
            return observational_binding_prediction
        observer_prediction = self._predict_observer_backend_frontier(profile, graph=graph)
        if observer_prediction is not None:
            return observer_prediction
        relationship_prediction = self._predict_relationship_frontier(profile, graph=graph)
        if relationship_prediction is not None:
            return relationship_prediction
        semantic_prediction = self._predict_semantic_maturity(profile, graph=graph)
        if semantic_prediction is not None:
            return semantic_prediction
        available = {item.casefold() for item in (available_capabilities or [])}
        missing_capabilities = [item for item in profile.expected_capabilities if item.casefold() not in available]
        if missing_capabilities:
            capability = missing_capabilities[0]
            return PredictionReport(
                profile_id=profile.profile_id,
                predicted_status="blocked",
                probable_component="capability_matching",
                probable_contract=self._first(profile.involved_contracts),
                probable_capability=capability,
                confidence=0.9,
                dependency_chain=self._chain(graph, capability=capability),
                hypothesis="A required cognitive or observational capability is not declared as available.",
                reason_codes=["PREDICTED_CAPABILITY_MISSING"],
                evidence_refs=[f"profile:{profile.profile_id}", f"capability:{capability}"],
            )
        if profile.expected_artifacts and not profile.involved_contracts:
            return PredictionReport(
                profile_id=profile.profile_id,
                predicted_status="partial",
                probable_component="artifact_contract",
                confidence=0.65,
                dependency_chain=self._chain(graph),
                hypothesis="Artifacts are expected but no explicit contract was declared for them.",
                reason_codes=["PREDICTED_ARTIFACT_CONTRACT_GAP"],
                evidence_refs=[f"profile:{profile.profile_id}"],
            )
        return PredictionReport(
            profile_id=profile.profile_id,
            predicted_status="ready",
            probable_component=None,
            confidence=0.7,
            dependency_chain=self._chain(graph),
            hypothesis="Declared capabilities and contracts are sufficient for a dry-run prediction.",
            reason_codes=[],
            evidence_refs=[f"profile:{profile.profile_id}"],
        )

    def _predict_semantic_ingress(self, profile: FireTestProfile, *, graph: DependencyGraph | None) -> PredictionReport | None:
        ingress = profile.metadata.get("semantic_ingress") if isinstance(profile.metadata.get("semantic_ingress"), dict) else {}
        checks = [
            ("encoding_status", {"degraded", "invalid"}, "encoding", "PREDICTED_ENCODING_DEGRADATION", "Prompt encoding is declared as degraded before semantic routing."),
            ("semantic_normalization_status", {"degraded", "invalid"}, "semantic_normalization", "PREDICTED_SEMANTIC_NORMALIZATION_FAILURE", "Prompt normalization is declared as insufficient for stable proposition extraction."),
            ("state_effect_status", {"ambiguous", "invalid", "unknown"}, "state_effects", "PREDICTED_STATE_EFFECT_AMBIGUITY", "State effect resolution is declared as ambiguous before contract selection."),
            ("intent_status", {"ambiguous", "invalid", "unknown"}, "intent_resolution", "PREDICTED_INTENT_AMBIGUITY", "Intent arbitration is declared as ambiguous before task bootstrap."),
            ("operation_contract_status", {"mismatch", "invalid", "unknown"}, "operation_contract_selection", "PREDICTED_OPERATION_CONTRACT_MISMATCH", "Operation contract selection is declared as incompatible with semantic effects."),
        ]
        for key, blocked_values, component, reason_code, hypothesis in checks:
            value = str(ingress.get(key) or "").casefold()
            if value in blocked_values:
                return PredictionReport(
                    profile_id=profile.profile_id,
                    predicted_status="blocked",
                    probable_component=component,
                    probable_contract=self._first(profile.involved_contracts),
                    confidence=float(ingress.get("confidence") or 0.8),
                    dependency_chain=self._chain(graph),
                    hypothesis=hypothesis,
                    reason_codes=[reason_code],
                    evidence_refs=[f"profile:{profile.profile_id}", f"semantic_ingress:{key}"],
                )
        return None

    def _predict_semantic_maturity(self, profile: FireTestProfile, *, graph: DependencyGraph | None) -> PredictionReport | None:
        maturity = profile.metadata.get("semantic_maturity") if isinstance(profile.metadata.get("semantic_maturity"), dict) else {}
        phase_policy = profile.metadata.get("phase_semantic_completion_policy") if isinstance(profile.metadata.get("phase_semantic_completion_policy"), dict) else {}
        policy_checks = [
            (
                "partial_artifact_acceptance",
                {"required", "missing", "undecided", "blocked"},
                "phase_semantic_completion_policy",
                "PARTIAL_ARTIFACT_ACCEPTANCE_REQUIRED",
                "A partial evidence-bound artifact is expected to need an explicit phase completion policy before the phase can complete.",
            ),
            (
                "completion_projection",
                {"null", "missing", "not_projected"},
                "completion_projection",
                "TERMINAL_COMPLETION_NULL",
                "A terminal phase result is expected to lack an explicit Completion projection.",
            ),
            (
                "lifecycle_timeout_finding",
                {"stale", "projection_artifact", "generic"},
                "validation_projection",
                "STALE_TASKRUN_LIFECYCLE_TIMEOUT_FINDING",
                "A generic lifecycle timeout finding is expected to hide the real semantic completion frontier.",
            ),
            (
                "phase_dependency_limitation",
                {"partial", "limited", "requires_policy"},
                "phase_dependency",
                "PHASE_DEPENDENCY_PARTIAL_LIMITATION",
                "Downstream phases are expected to require a policy decision before consuming a partial upstream artifact.",
            ),
            (
                "semantic_finalization_handoff",
                {"missing", "not_persisted", "preempted", "blocked"},
                "semantic_completion_finalization_handoff",
                "SEMANTIC_COMPLETION_FINALIZATION_HANDOFF_MISSING",
                "A semantic completion decision is expected to be available but not yet persisted before lifecycle repair.",
            ),
            (
                "store_repair_preemption",
                {"true", "preempted", "repair_won"},
                "task_run_store_repair_guard",
                "TASKRUNSTORE_REPAIR_PREEMPTS_SEMANTIC_COMPLETION",
                "TaskRunStore repair is expected to preempt semantic completion finalization.",
            ),
            (
                "semantic_result_persistence",
                {"missing", "failed", "not_persisted"},
                "semantic_result_persistence",
                "SEMANTIC_RESULT_NOT_PERSISTED_BEFORE_LIFECYCLE_REPAIR",
                "A semantic terminal result is expected to be missing before lifecycle repair.",
            ),
            (
                "stale_timeout_after_artifact_state",
                {"true", "stale", "dominant"},
                "validation_projection",
                "STALE_TASKRUN_LIFECYCLE_TIMEOUT_AFTER_ARTIFACT_STATE",
                "A stale lifecycle timeout is expected to remain dominant after semantic artifact state exists.",
            ),
        ]
        for key, blocked_values, component, reason_code, hypothesis in policy_checks:
            value = str(phase_policy.get(key) or "").casefold()
            if value in blocked_values:
                return PredictionReport(
                    profile_id=profile.profile_id,
                    predicted_status="blocked",
                    probable_component=component,
                    probable_contract=self._first(profile.involved_contracts),
                    probable_capability=str(phase_policy.get("capability_id") or "phase_semantic_completion_policy"),
                    confidence=float(phase_policy.get("confidence") or 0.84),
                    dependency_chain=self._chain(graph),
                    hypothesis=hypothesis,
                    reason_codes=[reason_code],
                    evidence_refs=[f"profile:{profile.profile_id}", f"phase_semantic_completion_policy:{key}"],
                )
        checks = [
            (
                "evidence_availability",
                {"missing", "insufficient", "blocked", "unknown"},
                "evidence_recording",
                "PREDICTED_EVIDENCE_AVAILABILITY_GAP",
                "Required attributes are declared, but evidence availability is insufficient for semantic validation.",
            ),
            (
                "knowledge_availability",
                {"missing", "insufficient", "blocked", "unknown"},
                "knowledge_representation",
                "PREDICTED_KNOWLEDGE_AVAILABILITY_GAP",
                "Evidence is not expected to compile into enough knowledge records for the contract.",
            ),
            (
                "semantic_completion",
                {"partial", "blocked", "insufficient", "unknown"},
                "semantic_coverage",
                "PREDICTED_SEMANTIC_COMPLETION_GAP",
                "Semantic coverage is expected to remain incomplete even if structural artifacts materialize.",
            ),
            (
                "truth_readiness",
                {"not_ready", "blocked", "unsafe", "unknown"},
                "truth_readiness",
                "PREDICTED_TRUTH_READINESS_GAP",
                "Speaker Truth is not expected to be safe because assertions are not fully evidence-backed.",
            ),
            (
                "validation_probability",
                {"low", "blocked", "unlikely"},
                "validation",
                "PREDICTED_VALIDATION_PROBABILITY_LOW",
                "Validation is predicted to block because semantic evidence or knowledge is insufficient.",
            ),
        ]
        for key, blocked_values, component, reason_code, hypothesis in checks:
            value = str(maturity.get(key) or "").casefold()
            if value in blocked_values:
                return PredictionReport(
                    profile_id=profile.profile_id,
                    predicted_status="blocked",
                    probable_component=component,
                    probable_contract=self._first(profile.involved_contracts),
                    probable_capability=str(maturity.get("probable_capability") or "") or None,
                    confidence=float(maturity.get("confidence") or 0.82),
                    dependency_chain=self._chain(graph),
                    hypothesis=hypothesis,
                    reason_codes=[reason_code],
                    evidence_refs=[f"profile:{profile.profile_id}", f"semantic_maturity:{key}"],
                )
        return None

    def _predict_project_analysis_frontier(self, profile: FireTestProfile, *, graph: DependencyGraph | None) -> PredictionReport | None:
        analysis = profile.metadata.get("project_analysis_cognition") if isinstance(profile.metadata.get("project_analysis_cognition"), dict) else {}
        if not analysis and not any(self._mentions_project_analysis(stage) for stage in profile.expected_pipeline):
            return None
        reason_code = str(analysis.get("reason_code") or "").strip()
        known_reason_components = {
            "PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED": "ProjectAnalysisService",
            "PROJECT_ANALYSIS_FILE_SKIPPED_BY_SINGLE_FILE_BUDGET": "FileContextBuilder",
            "PROJECT_ANALYSIS_PARTIAL_CONTEXT_AVAILABLE": "ProjectAnalysisService",
            "PROJECT_ANALYSIS_PARTIAL_CONTEXT_INSUFFICIENT": "ProjectAnalysisService",
            "PROJECT_ANALYSIS_SELECTION_READ_COOPERATION_MISSING": "ProjectAnalysisService",
            "MEDIA_CORPUS_ROOT_HANDOFF_READY": "ProjectAnalysisService",
            "MEDIA_CORPUS_ROOT_NO_INVENTORY_ELIGIBLE_ENTITIES": "ProjectAnalysisService",
            "PROJECT_ANALYSIS_ROOT_ROLE_FILE_SELECTION_MISMATCH": "ProjectAnalysisService",
            "PROJECT_ANALYSIS_CORPUS_HANDOFF_FAILED": "ProjectAnalysisService",
        }
        if reason_code in known_reason_components:
            partial_reasons = {"PROJECT_ANALYSIS_PARTIAL_CONTEXT_AVAILABLE", "MEDIA_CORPUS_ROOT_HANDOFF_READY"}
            return PredictionReport(
                profile_id=profile.profile_id,
                predicted_status="partial" if reason_code in partial_reasons else "blocked",
                probable_component=str(analysis.get("component") or known_reason_components[reason_code]),
                probable_contract=self._first(profile.involved_contracts),
                confidence=float(analysis.get("confidence") or 0.8),
                dependency_chain=self._chain(graph),
                hypothesis="ProjectAnalysis role-aware source/inventory handoff is declared as the current cognitive frontier.",
                reason_codes=[reason_code],
                evidence_refs=[f"profile:{profile.profile_id}", "project_analysis_cognition:reason_code"],
            )
        checks = [
            (
                "corpus_handoff_status",
                {"missing", "blocked", "failed"},
                "ProjectAnalysisService",
                "PROJECT_ANALYSIS_CORPUS_HANDOFF_FAILED",
                "ProjectAnalysis is expected to lack a governed corpus handoff before artifact runtime.",
            ),
            (
                "root_role_file_selection_status",
                {"mismatch", "source_policy_applied_to_corpus", "blocked"},
                "ProjectAnalysisService",
                "PROJECT_ANALYSIS_ROOT_ROLE_FILE_SELECTION_MISMATCH",
                "ProjectAnalysis is expected to confuse source-readable selection with corpus inventory eligibility.",
            ),
            (
                "file_read_status",
                {"single_file_budget_exceeded", "budget_exceeded", "timeout", "blocked"},
                "ProjectAnalysisService",
                "PROJECT_ANALYSIS_SINGLE_FILE_READ_BUDGET_EXCEEDED",
                "ProjectAnalysis is expected to block on bounded single-file read budget cooperation.",
            ),
            (
                "partial_context_status",
                {"insufficient", "missing", "blocked", "unknown"},
                "ProjectAnalysisService",
                "PROJECT_ANALYSIS_PARTIAL_CONTEXT_INSUFFICIENT",
                "ProjectAnalysis is expected to lack enough partial context to continue safely.",
            ),
            (
                "cooperation_status",
                {"missing", "not_applied", "blocked", "unknown"},
                "ProjectAnalysisService",
                "PROJECT_ANALYSIS_SELECTION_READ_COOPERATION_MISSING",
                "ProjectAnalysis selection and read stages are not expected to cooperate with budgets.",
            ),
        ]
        for key, blocked_values, component, mapped_reason, hypothesis in checks:
            value = str(analysis.get(key) or "").casefold()
            if value in blocked_values:
                return PredictionReport(
                    profile_id=profile.profile_id,
                    predicted_status="blocked",
                    probable_component=component,
                    probable_contract=self._first(profile.involved_contracts),
                    confidence=float(analysis.get("confidence") or 0.8),
                    dependency_chain=self._chain(graph),
                    hypothesis=hypothesis,
                    reason_codes=[mapped_reason],
                    evidence_refs=[f"profile:{profile.profile_id}", f"project_analysis_cognition:{key}"],
                )
        return None

    def _mentions_project_analysis(self, stage: str) -> bool:
        value = stage.casefold()
        return any(token in value for token in ("projectanalysis", "project_analysis", "file_read", "partial_context", "selection_read", "corpus_handoff", "root_role_file_selection"))

    def _predict_public_runtime_boundary(self, profile: FireTestProfile, *, graph: DependencyGraph | None) -> PredictionReport | None:
        boundary = profile.metadata.get("public_response_boundary") if isinstance(profile.metadata.get("public_response_boundary"), dict) else {}
        if not boundary and not any(self._mentions_public_runtime_boundary(stage) for stage in profile.expected_pipeline):
            return None
        checks = [
            (
                "response_mode",
                {"synchronous", "sync_wait", "client_timeout"},
                "PublicRuntimeResponsePolicy",
                "PUBLIC_CHAT_RESPONSE_BOUNDARY",
                "The public response boundary is expected to block on synchronous runtime waiting.",
            ),
            (
                "accepted_running_status",
                {"missing", "disabled", "not_available", "blocked"},
                "PublicRuntimeResponsePolicy",
                "PUBLIC_RUNTIME_CONTINUATION_NOT_AVAILABLE",
                "The runtime is not expected to return accepted_running for a continuable long run.",
            ),
            (
                "timeout_blocked_status",
                {"missing", "disabled", "not_available", "blocked"},
                "PublicRuntimeResponsePolicy",
                "PUBLIC_RESPONSE_TIMEOUT_BLOCKED",
                "The runtime is not expected to produce a governed timeout_blocked response.",
            ),
            (
                "artifact_worker_terminalization",
                {"missing", "stalled", "gap", "orphaned", "blocked"},
                "artifact_worker_terminalization_guard",
                "ACCEPTED_RUNNING_ARTIFACT_WORKER_TERMINALIZATION_GAP",
                "An accepted-running artifact worker is expected to need a terminalization guard.",
            ),
            (
                "artifact_runtime_status",
                {"stalled_after_artifact_creation_started", "artifact_started_without_terminal", "orphaned_after_accept"},
                "artifact_worker_terminalization_guard",
                "ARTIFACT_RUNTIME_STALLED_AFTER_ARTIFACT_CREATION_STARTED",
                "Artifact runtime is expected to stall after artifact creation starts without a terminal result.",
            ),
            (
                "fact_source_binding",
                {
                    "stalled",
                    "blocked",
                    "attribute_observation_projection",
                    "evidence_ref_resolution",
                    "evidence_set_materialization",
                    "source_provenance_binding",
                    "source_binding_bound_check",
                    "bound_exceeded",
                },
                "ContractDrivenPerceptionService",
                "PERCEPTION_FACT_SOURCE_BINDING_FRONTIER",
                "Fact source binding is expected to need governed attribute observations, evidence refs and provenance materialization.",
            ),
            (
                "perception_fact_projection",
                {
                    "stalled",
                    "blocked",
                    "source_binding",
                    "candidate_projection",
                    "derivation",
                    "provenance_binding",
                    "deduplication",
                    "validation_projection",
                    "bound_exceeded",
                    "complexity_budget_exceeded",
                },
                "ContractDrivenPerceptionService",
                "PERCEPTION_FACT_PROJECTION_FRONTIER",
                "Contract-driven fact projection is expected to need explicit semantics, provenance and bounded derivation.",
            ),
            (
                "perception_compile_boundary",
                {
                    "stalled",
                    "blocked",
                    "payload_bound_exceeded",
                    "budget_exceeded",
                    "requirement_resolution",
                    "entity_projection",
                    "observation_binding",
                    "relationship_projection",
                    "fact_projection",
                    "payload_assembly",
                },
                "ContractDrivenPerceptionService",
                "PERCEPTION_PAYLOAD_COMPILE_BOUNDARY",
                "Contract-driven perception payload compilation is expected to be the current bounded materialization frontier.",
            ),
            (
                "music_inventory_post_selection_stage",
                {
                    "after_entity_selection",
                    "perception_payload_compile",
                    "contract_perception",
                    "row_binding",
                    "metadata_coverage",
                    "csv_streaming",
                    "semantic_profile",
                    "inventory_sufficiency",
                    "artifact_persist",
                    "stalled",
                },
                "ReadonlyAnalysisArtifactRuntimeService",
                "MUSIC_INVENTORY_POST_SELECTION_RENDER_PERCEPTION_STALL",
                "The media inventory artifact is expected to need post-selection render/perception stall localization.",
            ),
            (
                "result_endpoint_after_artifact_start",
                {"404", "missing", "not_available"},
                "artifact_worker_terminalization_guard",
                "RESULT_ENDPOINT_404_AFTER_ARTIFACT_START",
                "The result endpoint is expected to remain unavailable after artifact creation starts.",
            ),
            (
                "artifact_registry_status",
                {"legacy_too_large", "legacy_invalid", "corrupt", "unreadable"},
                "ArtifactRegistryRepository",
                "ARTIFACT_REGISTRY_LEGACY_PROJECTION_UNREADABLE",
                "The legacy monolithic artifact registry is expected to block artifact creation.",
            ),
            (
                "payload_hydration_status",
                {"json_decode_error", "schema_mismatch", "too_large_for_inline", "invalid_payload_type"},
                "PayloadHydrationBoundary",
                "PAYLOAD_REF_HYDRATION_BOUNDARY",
                "Payload/ref hydration is expected to require a bounded, typed projection.",
            ),
            (
                "result_finalization_status",
                {"missing", "incomplete", "blocked", "unknown"},
                "PublicRunFinalizationGuard",
                "PUBLIC_RUNTIME_RESULT_FINALIZATION_MISSING",
                "Public runtime terminalization may not produce a coherent final result.",
            ),
            (
                "terminal_result_status",
                {"missing", "absent", "not_persisted"},
                "PublicRunFinalizationGuard",
                "TERMINAL_RESULT_MISSING",
                "A terminal TaskRun is expected to lack a persisted terminal result.",
            ),
            (
                "partial_artifact_result_finalization",
                {"missing", "blocked", "gap", "not_persisted"},
                "PublicRunFinalizationGuard",
                "PARTIAL_ARTIFACT_RESULT_FINALIZATION_GAP",
                "Partial or blocked artifact state is expected to need conservative terminal result finalization.",
            ),
            (
                "blocked_run_result_persistence",
                {"missing", "blocked", "gap", "not_persisted"},
                "PublicRunFinalizationGuard",
                "BLOCKED_RUN_RESULT_PERSISTENCE_GAP",
                "A blocked run is expected to need an explicit persisted TaskRunResult.",
            ),
            (
                "endpoint_health",
                {"slow", "inconsistent", "blocked", "unknown"},
                "UniversalTaskSessionService",
                "PUBLIC_ENDPOINT_SUMMARY_SLOW_OR_INCONSISTENT",
                "Public polling endpoints are predicted to be slow or inconsistent.",
            ),
            (
                "phase_dependency_boundary",
                {"text_false_positive", "ambiguous", "blocked"},
                "ReadonlyAnalysisArtifactRuntimeService",
                "PHASE_DEPENDENCY_TEXT_FALSE_POSITIVE",
                "Cognitive phase references may be interpreted as operational artifact dependencies.",
            ),
            (
                "artifact_lifecycle_status",
                {"late_rejected", "late_artifact_rejected", "post_terminal_reject"},
                "ArtifactRenderLifecycle",
                "ARTIFACT_RENDER_LATE_ARTIFACT_REJECTED",
                "Artifact rendering is expected to encounter a governed late artifact rejection.",
            ),
            (
                "preacceptance_status",
                {"heavy_work_detected", "budget_exceeded", "blocked"},
                "PublicPreAcceptancePolicy",
                "PUBLIC_RUNTIME_PREACCEPTANCE_HEAVY_WORK_DETECTED",
                "Public pre-acceptance is expected to perform work that belongs inside a TaskRun.",
            ),
            (
                "taskrun_bootstrap_status",
                {"not_reached", "missing", "blocked"},
                "TaskRuntimeService",
                "PUBLIC_RUNTIME_CREATE_RUN_NOT_REACHED",
                "Public runtime is not expected to reach TaskRun bootstrap before the response boundary.",
            ),
            (
                "phase_progression_status",
                {"stop_condition_required", "invalid_post_block_attempt"},
                "PhaseProgressionGate",
                "PHASE_PROGRESSION_STOP_CONDITION_REQUIRED",
                "The phase progression harness is expected to need a first-block stop condition.",
            ),
        ]
        for key, blocked_values, component, reason_code, hypothesis in checks:
            value = str(boundary.get(key) or "").casefold()
            if value in blocked_values:
                return PredictionReport(
                    profile_id=profile.profile_id,
                    predicted_status="blocked",
                    probable_component=component,
                    probable_contract=self._first(profile.involved_contracts),
                    confidence=float(boundary.get("confidence") or 0.8),
                    dependency_chain=self._chain(graph),
                    hypothesis=hypothesis,
                    reason_codes=[reason_code],
                    evidence_refs=[f"profile:{profile.profile_id}", f"public_response_boundary:{key}"],
                )
        return None

    def _mentions_public_runtime_boundary(self, stage: str) -> bool:
        value = stage.casefold()
        return any(
            token in value
            for token in (
                "public_response",
                "accepted_running",
                "timeout_blocked",
                "public_endpoint",
                "phase_dependency",
                "preacceptance",
                "pre_acceptance",
                "taskrun_bootstrap",
                "phase_progression",
                "skipped_due_to_prior_block",
                "artifact_worker",
                "artifact_creation_started",
                "artifact_started_without_terminal",
                "result_endpoint_404",
            )
        )

    def _predict_observer_backend_frontier(self, profile: FireTestProfile, *, graph: DependencyGraph | None) -> PredictionReport | None:
        media = profile.metadata.get("media_metadata_capability") if isinstance(profile.metadata.get("media_metadata_capability"), dict) else {}
        if not media:
            return None
        checks = [
            (
                "capability_status",
                {"missing", "not_registered", "unknown"},
                "capability_registry",
                "CAPABILITY_NOT_REGISTERED",
                "Required media metadata capability is not registered before observation planning.",
            ),
            (
                "backend_status",
                {"not_configured", "missing_dependency", "backend_unavailable", "unknown"},
                "backend_not_configured",
                self._backend_reason_code(media),
                "Media metadata capability is known, but backend availability is insufficient for execution.",
            ),
            (
                "observer_binding_status",
                {"missing", "not_bound", "invalid", "unknown"},
                "observer_binding",
                "OBSERVER_BINDING_MISSING",
                "Capability exists, but no governed observer binding is available.",
            ),
            (
                "execution_status",
                {"failed", "blocked", "timeout", "observer_error"},
                "observer_execution",
                "OBSERVER_EXECUTION_FAILED",
                "Observer execution is expected to fail before valid evidence can be recorded.",
            ),
            (
                "evidence_recording_status",
                {"failed", "missing", "blocked", "no_evidence"},
                "evidence_recording",
                "EVIDENCE_RECORDING_FAILED",
                "Observer execution is not expected to produce valid EvidenceRecord objects.",
            ),
            (
                "evidence_coverage_status",
                {"insufficient", "partial", "blocked", "low"},
                "evidence_coverage",
                "EVIDENCE_COVERAGE_INSUFFICIENT",
                "Evidence may exist, but contract coverage is predicted to remain insufficient.",
            ),
            (
                "semantic_validation_status",
                {"blocked", "failed", "unlikely"},
                "validation",
                "SEMANTIC_VALIDATION_BLOCKED",
                "Semantic validation is predicted to block after observational evidence assessment.",
            ),
        ]
        for key, blocked_values, component, reason_code, hypothesis in checks:
            value = str(media.get(key) or "").casefold()
            if value in blocked_values:
                return PredictionReport(
                    profile_id=profile.profile_id,
                    predicted_status="blocked",
                    probable_component=component,
                    probable_contract=self._first(profile.involved_contracts),
                    probable_capability=str(media.get("capability_id") or "media_metadata_reader"),
                    confidence=float(media.get("confidence") or 0.84),
                    dependency_chain=self._chain(graph, capability=str(media.get("capability_id") or "media_metadata_reader")),
                    hypothesis=hypothesis,
                    reason_codes=[reason_code],
                    evidence_refs=[f"profile:{profile.profile_id}", f"media_metadata_capability:{key}"],
                )
        return None

    def _backend_reason_code(self, media: dict[str, Any]) -> str:
        backend_status = str(media.get("backend_status") or "").casefold()
        if backend_status == "missing_dependency":
            return "DEPENDENCY_MISSING"
        if backend_status == "backend_unavailable":
            return "BACKEND_NOT_CONFIGURED"
        return "BACKEND_NOT_CONFIGURED"

    def _predict_media_inventory_sufficiency_frontier(self, profile: FireTestProfile, *, graph: DependencyGraph | None) -> PredictionReport | None:
        inventory = self._metadata_dict(profile, "media_inventory_sufficiency") or self._metadata_dict(profile, "inventory_sufficiency")
        metadata_coverage = self._metadata_dict(profile, "metadata_coverage") or self._metadata_dict(profile, "metadata_coverage_summary")
        media = self._metadata_dict(profile, "media_metadata_capability")
        if not inventory and not metadata_coverage:
            return None
        checks: list[tuple[bool, str, str, str, str, float]] = [
            (
                str(metadata_coverage.get("status") or "").casefold() in {"not_configured", "not_run", "missing"},
                "media_metadata_observation",
                "media_metadata_reader",
                "MEDIA_METADATA_PROBE_REQUIRED",
                "The artifact contract needs governed media metadata observation before inventory sufficiency can be claimed.",
                float(metadata_coverage.get("confidence") or media.get("confidence") or 0.84),
            ),
            (
                str(metadata_coverage.get("status") or "").casefold() in {"partial", "incomplete", "blocked"},
                "media_metadata_observation",
                "media_metadata_reader",
                "MEDIA_METADATA_OBSERVATION_INCOMPLETE",
                "Media metadata observation is present but does not cover the selected corpus rows.",
                float(metadata_coverage.get("confidence") or media.get("confidence") or 0.84),
            ),
            (
                str(inventory.get("coverage_status") or inventory.get("row_coverage_status") or "").casefold() in {"insufficient", "partial", "windowed", "blocked"},
                "media_inventory_sufficiency",
                "media_metadata_reader",
                "MEDIA_INVENTORY_COVERAGE_INSUFFICIENT",
                "The media inventory contract requires more governed corpus row coverage than is currently available.",
                float(inventory.get("confidence") or 0.86),
            ),
            (
                str(inventory.get("schema_alias_status") or "").casefold() in {"noisy", "mismatch", "blocked"},
                "media_inventory_schema",
                "artifact_semantic_contract",
                "MEDIA_INVENTORY_SCHEMA_ALIAS_NOISE",
                "Rendered schema aliases are predicted to obscure canonical inventory sufficiency.",
                float(inventory.get("confidence") or 0.82),
            ),
            (
                str(inventory.get("status") or "").casefold() in {"blocked", "insufficient", "not_satisfied"},
                "media_inventory_sufficiency",
                "artifact_semantic_contract",
                str(inventory.get("reason_code") or "MEDIA_INVENTORY_COMPLETE_SUFFICIENCY_REQUIRED"),
                "The inventory sufficiency policy is expected to block complete phase readiness.",
                float(inventory.get("confidence") or 0.87),
            ),
            (
                inventory.get("safe_to_use") is False,
                "media_inventory_sufficiency",
                "artifact_semantic_contract",
                "MEDIA_INVENTORY_SAFE_TO_USE_FALSE",
                "The artifact may be evidence-bound but is not safe for phase success claims.",
                float(inventory.get("confidence") or 0.87),
            ),
        ]
        for triggered, component, capability, reason_code, hypothesis, confidence in checks:
            if not triggered:
                continue
            return PredictionReport(
                profile_id=profile.profile_id,
                predicted_status="blocked",
                probable_component=component,
                probable_contract=self._first(profile.involved_contracts),
                probable_capability=capability,
                confidence=confidence,
                dependency_chain=self._chain(graph, capability=capability),
                hypothesis=hypothesis,
                reason_codes=[reason_code],
                evidence_refs=[f"profile:{profile.profile_id}", "media_inventory_sufficiency"],
            )
        return None

    def _metadata_dict(self, profile: FireTestProfile, key: str) -> dict[str, Any]:
        value = profile.metadata.get(key) if isinstance(profile.metadata, dict) else None
        return value if isinstance(value, dict) else {}

    def _predict_observational_binding_frontier(self, profile: FireTestProfile, *, graph: DependencyGraph | None) -> PredictionReport | None:
        binding = profile.metadata.get("observational_binding") if isinstance(profile.metadata.get("observational_binding"), dict) else {}
        artifact_binding = profile.metadata.get("artifact_evidence_binding") if isinstance(profile.metadata.get("artifact_evidence_binding"), dict) else {}
        if artifact_binding and not binding:
            binding = {
                "evidence_binding_status": artifact_binding.get("status") or artifact_binding.get("evidence_binding_status"),
                "confidence": artifact_binding.get("confidence"),
                "capability_id": artifact_binding.get("capability_id"),
                "metadata_source": "artifact_evidence_binding",
            }
        if not binding:
            return None
        checks = [
            (
                "root_policy_status",
                {"blocked", "denied", "policy_blocked"},
                "root_binding",
                "CORPUS_ROOT_POLICY_BLOCKED",
                "A declared corpus/library root is expected to be blocked by root observation policy.",
            ),
            (
                "root_role_projection_status",
                {"missing", "not_projected", "blocked", "insufficient"},
                "observed_entity_compilation",
                "OBSERVED_ENTITY_ROLE_PROJECTION_MISSING",
                "Declared corpus/library roots are expected to lack observed entity role projection.",
            ),
            (
                "corpus_observation_status",
                {"missing", "not_executed", "unavailable", "blocked"},
                "observed_entity_compilation",
                "CORPUS_OBSERVATION_EXECUTION_UNAVAILABLE",
                "Corpus observation is expected not to execute before artifact materialization.",
            ),
            (
                "entity_selection_status",
                {"empty", "blocked", "insufficient"},
                "semantic_entity_selection",
                "MEDIA_CORPUS_ENTITY_SELECTION_EMPTY",
                "Semantic artifact execution is expected to lack corpus/library entity selection.",
            ),
            (
                "evidence_binding_status",
                {"missing", "blocked", "insufficient"},
                "artifact_evidence_binding",
                "ARTIFACT_EVIDENCE_BINDING_MISSING",
                "Selected entities are expected to lack minimum evidence refs for artifact rows.",
            ),
            (
                "observational_binding_status",
                {"missing", "not_bound", "blocked", "insufficient"},
                "observational_binding",
                "OBSERVATIONAL_BINDING_INSUFFICIENT",
                "The artifact contract is expected to require observations that are not bound to evidence.",
            ),
            (
                "media_metadata_status",
                {"not_configured", "missing_dependency", "blocked"},
                "media_metadata_capability",
                "MEDIA_METADATA_CAPABILITY_NOT_CONFIGURED",
                "Media metadata is expected to remain unavailable and must be represented as a limitation.",
            ),
            (
                "semantic_inventory_status",
                {"partial", "blocked", "insufficient"},
                "artifact_semantic_contract",
                "MUSIC_INVENTORY_PARTIAL_EVIDENCE",
                "The media corpus inventory is expected to remain partial under current evidence coverage.",
            ),
        ]
        for key, blocked_values, component, reason_code, hypothesis in checks:
            value = str(binding.get(key) or "").casefold()
            if value in blocked_values:
                return PredictionReport(
                    profile_id=profile.profile_id,
                    predicted_status="blocked",
                    probable_component=component,
                    probable_contract=self._first(profile.involved_contracts),
                    probable_capability=str(binding.get("capability_id") or "artifact_observation_binding"),
                    confidence=float(binding.get("confidence") or 0.83),
                    dependency_chain=self._chain(graph, capability=str(binding.get("capability_id") or "artifact_observation_binding")),
                    hypothesis=hypothesis,
                    reason_codes=[reason_code],
                    evidence_refs=[f"profile:{profile.profile_id}", f"{binding.get('metadata_source') or 'observational_binding'}:{key}"],
                )
        return None

    def _predict_relationship_frontier(self, profile: FireTestProfile, *, graph: DependencyGraph | None) -> PredictionReport | None:
        relationship = profile.metadata.get("relationship_cognition") if isinstance(profile.metadata.get("relationship_cognition"), dict) else {}
        if not relationship and not any(self._mentions_relationship_cognition(stage) for stage in profile.expected_pipeline):
            return None
        checks = [
            (
                "capability_status",
                {"missing", "not_registered", "unknown"},
                "capability_registry",
                "MEDIA_RELATIONSHIP_CAPABILITY_MISSING",
                "Relationship cognition is expected, but the governed relationship capability is not registered.",
            ),
            (
                "evidence_status",
                {"missing", "insufficient", "blocked", "unknown"},
                "relationship_evidence",
                "RELATIONSHIP_EVIDENCE_INSUFFICIENT",
                "Relationship candidates are expected to lack sufficient evidence signals.",
            ),
            (
                "provenance_status",
                {"missing", "incomplete", "blocked", "unknown"},
                "relationship_provenance",
                "RELATIONSHIP_PROVENANCE_MISSING",
                "Relationship candidates are expected to lack complete provenance traces.",
            ),
            (
                "validation_policy_status",
                {"missing", "not_configured", "blocked", "unknown"},
                "relationship_validation_policy",
                "RELATIONSHIP_VALIDATION_POLICY_MISSING",
                "Relationship candidates are expected, but no governed validation policy is available.",
            ),
            (
                "ambiguity_status",
                {"ambiguous", "unresolved", "blocked", "unknown"},
                "relationship_ambiguity",
                "RELATIONSHIP_AMBIGUITY_UNRESOLVED",
                "Relationship candidates are expected to remain ambiguous before final validation readiness.",
            ),
            (
                "conflict_status",
                {"present", "unresolved", "blocked", "conflicted"},
                "relationship_conflict_resolution",
                "RELATIONSHIP_CONFLICT_BLOCKED",
                "Relationship candidates are expected to carry conflicts that block readiness.",
            ),
            (
                "confidence_status",
                {"insufficient", "low", "conflicted", "unknown"},
                "relationship_confidence",
                "RELATIONSHIP_CONFIDENCE_INSUFFICIENT",
                "Relationship candidates are expected to have insufficient confidence for future readiness.",
            ),
            (
                "truth_policy_status",
                {"not_satisfied", "unsatisfied", "blocked", "unsafe", "unknown"},
                "relationship_truth_policy",
                "RELATIONSHIP_TRUTH_POLICY_NOT_SATISFIED",
                "Relationship readiness may exist, but Truth policy is not satisfied for final claims.",
            ),
            (
                "validation_status",
                {"required", "missing", "blocked", "not_validated"},
                "relationship_validation",
                "RELATIONSHIP_VALIDATION_REQUIRED",
                "Relationship candidates may be observed, but final relationship validation is not available.",
            ),
        ]
        for key, blocked_values, component, reason_code, hypothesis in checks:
            value = str(relationship.get(key) or "").casefold()
            if value in blocked_values:
                return PredictionReport(
                    profile_id=profile.profile_id,
                    predicted_status="blocked",
                    probable_component=component,
                    probable_contract=self._first(profile.involved_contracts),
                    probable_capability=str(relationship.get("capability_id") or "media_relationship_candidate_detector"),
                    confidence=float(relationship.get("confidence") or 0.78),
                    dependency_chain=self._chain(graph, capability=str(relationship.get("capability_id") or "media_relationship_candidate_detector")),
                    hypothesis=hypothesis,
                    reason_codes=[reason_code],
                    evidence_refs=[f"profile:{profile.profile_id}", f"relationship_cognition:{key}"],
                )
        return None

    def _mentions_relationship_cognition(self, stage: str) -> bool:
        value = stage.casefold()
        return any(token in value for token in ("relationship", "sidecar_candidate", "relationship_evidence"))

    def _predict_workspace_role_boundary(self, profile: FireTestProfile, *, graph: DependencyGraph | None) -> PredictionReport | None:
        boundary = profile.metadata.get("workspace_role_boundary") if isinstance(profile.metadata.get("workspace_role_boundary"), dict) else {}
        checks = [
            ("root_role_status", {"missing", "ambiguous", "invalid", "not_applied"}, "entity_selection_policy", "PREDICTED_WORKSPACE_ROLE_BOUNDARY", "Workspace root roles are not sufficient for contract-aware entity selection."),
            ("entity_selection_policy_status", {"missing", "ambiguous", "invalid", "not_applied"}, "entity_selection_policy", "PREDICTED_ENTITY_SELECTION_POLICY_GAP", "Entity selection policy is not bound before artifact rendering."),
            ("corpus_observation_status", {"missing", "unobserved", "invalid"}, "observed_entity_compilation", "PREDICTED_CORPUS_ROOT_NOT_OBSERVED", "A declared corpus or library root is not represented in the observed entity graph."),
        ]
        for key, blocked_values, component, reason_code, hypothesis in checks:
            value = str(boundary.get(key) or "").casefold()
            if value in blocked_values:
                return PredictionReport(
                    profile_id=profile.profile_id,
                    predicted_status="blocked",
                    probable_component=component,
                    probable_contract=self._first(profile.involved_contracts),
                    confidence=float(boundary.get("confidence") or 0.85),
                    dependency_chain=self._chain(graph),
                    hypothesis=hypothesis,
                    reason_codes=[reason_code],
                    evidence_refs=[f"profile:{profile.profile_id}", f"workspace_role_boundary:{key}"],
                )
        return None

    def _chain(self, graph: DependencyGraph | None, *, capability: str | None = None) -> list[str]:
        if graph is None:
            return []
        if capability:
            wanted = f"capability:{''.join(ch if ch.isalnum() else '_' for ch in capability.casefold()).strip('_')}"
            node = next((item for item in graph.nodes if item.node_id == wanted), None)
            if node:
                return [node.node_id, *node.dependents]
        return [item.node_id for item in graph.nodes if item.node_type == "pipeline"]

    def _first(self, rows: list[str]) -> str | None:
        return rows[0] if rows else None


class CognitiveCoverageService:
    """Computes cognitive maturity from declared contracts and available capabilities."""

    def report(self, profile: FireTestProfile, *, available_capabilities: list[str] | None = None) -> CoverageReport:
        available = {item.casefold() for item in (available_capabilities or [])}
        capability_ratio = self._ratio(
            sum(1 for capability in profile.expected_capabilities if capability.casefold() in available),
            len(profile.expected_capabilities),
        )
        metrics = [
            self._metric("pipeline", 1.0 if profile.expected_pipeline else 0.0, "high", ["expected_pipeline"] if not profile.expected_pipeline else []),
            self._metric("contracts", 1.0 if profile.involved_contracts else 0.0, "high", ["involved_contracts"] if not profile.involved_contracts else []),
            self._metric("capabilities", capability_ratio, "critical", [item for item in profile.expected_capabilities if item.casefold() not in available]),
            self._metric("artifacts", 1.0 if profile.expected_artifacts else 0.0, "medium", ["expected_artifacts"] if not profile.expected_artifacts else []),
            self._metric("success_contract", 1.0 if profile.success_contract else 0.0, "high", ["success_contract"] if not profile.success_contract else []),
        ]
        metrics.extend(self._semantic_ingress_metrics(profile))
        metrics.extend(self._workspace_role_boundary_metrics(profile))
        metrics.extend(self._project_analysis_metrics(profile))
        metrics.extend(self._public_runtime_boundary_metrics(profile))
        metrics.extend(self._observer_backend_metrics(profile))
        metrics.extend(self._relationship_cognition_metrics(profile))
        metrics.extend(self._semantic_maturity_metrics(profile))
        overall = sum(item.coverage for item in metrics) / max(1, len(metrics))
        status = "ready" if overall >= 0.95 else "partial" if overall > 0 else "blocked"
        return CoverageReport(
            profile_id=profile.profile_id,
            metrics=metrics,
            overall_coverage=round(overall, 4),
            overall_status=status,
            metadata={"available_capability_count": len(available)},
        )

    def _semantic_ingress_metrics(self, profile: FireTestProfile) -> list[CoverageMetric]:
        ingress = profile.metadata.get("semantic_ingress") if isinstance(profile.metadata.get("semantic_ingress"), dict) else {}
        if not ingress and not any(self._mentions_semantic_ingress(stage) for stage in profile.expected_pipeline):
            return []
        checks = [
            ("encoding", "encoding_status", {"ok", "clean", "ready"}),
            ("semantic_ingress", "semantic_normalization_status", {"ok", "clean", "ready"}),
            ("state_effects", "state_effect_status", {"resolved", "ok", "ready"}),
            ("intent", "intent_status", {"resolved", "ok", "ready"}),
            ("operation_contract", "operation_contract_status", {"selected", "ok", "ready"}),
        ]
        metrics: list[CoverageMetric] = []
        for domain, key, ready_values in checks:
            value = str(ingress.get(key) or "").casefold()
            if value in ready_values:
                coverage = 1.0
                gaps: list[str] = []
            elif value:
                coverage = 0.0
                gaps = [value]
            else:
                coverage = 0.5 if any(domain in stage.casefold() for stage in profile.expected_pipeline) else 0.0
                gaps = [key]
            metrics.append(self._metric(domain, coverage, "high", gaps))
        return metrics

    def _mentions_semantic_ingress(self, stage: str) -> bool:
        value = stage.casefold()
        return any(token in value for token in ("text_ingress", "encoding", "semantic_normalization", "state_effect", "intent_resolution", "operation_contract"))

    def _workspace_role_boundary_metrics(self, profile: FireTestProfile) -> list[CoverageMetric]:
        boundary = profile.metadata.get("workspace_role_boundary") if isinstance(profile.metadata.get("workspace_role_boundary"), dict) else {}
        if not boundary and not any(self._mentions_workspace_role_boundary(stage) for stage in profile.expected_pipeline):
            return []
        checks = [
            ("workspace_role_boundary", "root_role_status", {"ok", "resolved", "ready"}),
            ("entity_selection_policy", "entity_selection_policy_status", {"ok", "applied", "ready"}),
            ("corpus_observation", "corpus_observation_status", {"ok", "observed", "ready"}),
        ]
        metrics: list[CoverageMetric] = []
        for domain, key, ready_values in checks:
            value = str(boundary.get(key) or "").casefold()
            if value in ready_values:
                coverage = 1.0
                gaps: list[str] = []
            elif value:
                coverage = 0.0
                gaps = [value]
            else:
                coverage = 0.5 if any(domain in stage.casefold() for stage in profile.expected_pipeline) else 0.0
                gaps = [key]
            metrics.append(self._metric(domain, coverage, "high", gaps))
        return metrics

    def _mentions_workspace_role_boundary(self, stage: str) -> bool:
        value = stage.casefold()
        return any(token in value for token in ("workspace_role", "entity_selection_policy", "root_role", "corpus_observation"))

    def _project_analysis_metrics(self, profile: FireTestProfile) -> list[CoverageMetric]:
        analysis = profile.metadata.get("project_analysis_cognition") if isinstance(profile.metadata.get("project_analysis_cognition"), dict) else {}
        if not analysis and not any(CognitiveGapPredictor()._mentions_project_analysis(stage) for stage in profile.expected_pipeline):
            return []
        checks = [
            ("project_analysis_file_read", "file_read_status", {"ok", "bounded", "cooperative", "partial"}),
            ("project_analysis_partial_context", "partial_context_status", {"available", "sufficient", "ready"}),
            ("project_analysis_selection_read_cooperation", "cooperation_status", {"active", "ready", "cooperative"}),
        ]
        metrics: list[CoverageMetric] = []
        for domain, key, ready_values in checks:
            value = str(analysis.get(key) or "").casefold()
            if value in ready_values:
                coverage = 1.0
                gaps: list[str] = []
            elif value:
                coverage = 0.0
                gaps = [value]
            else:
                coverage = 0.5 if any(domain in stage.casefold() for stage in profile.expected_pipeline) else 0.0
                gaps = [key]
            metrics.append(self._metric(domain, coverage, "high", gaps))
        return metrics

    def _public_runtime_boundary_metrics(self, profile: FireTestProfile) -> list[CoverageMetric]:
        boundary = profile.metadata.get("public_response_boundary") if isinstance(profile.metadata.get("public_response_boundary"), dict) else {}
        if not boundary and not any(CognitiveGapPredictor()._mentions_public_runtime_boundary(stage) for stage in profile.expected_pipeline):
            return []
        checks = [
            ("public_response_boundary", "response_mode", {"accepted_running", "timeout_blocked", "governed"}),
            ("public_response_acceptance", "accepted_running_status", {"available", "enabled", "ready"}),
            ("public_response_timeout_blocked", "timeout_blocked_status", {"available", "enabled", "ready"}),
            ("accepted_worker_terminalization", "artifact_worker_terminalization", {"guarded", "ready", "available"}),
            ("artifact_runtime_terminality", "artifact_runtime_status", {"terminalized", "ready", "guarded"}),
            ("result_endpoint_after_artifact_start", "result_endpoint_after_artifact_start", {"available", "ready", "200"}),
            ("public_result_finalization", "result_finalization_status", {"coherent", "available", "ready"}),
            ("public_endpoint_health", "endpoint_health", {"lightweight", "consistent", "ready"}),
            ("phase_dependency_boundary", "phase_dependency_boundary", {"separated", "ready", "explicit_only"}),
            ("public_preacceptance", "preacceptance_status", {"lightweight", "ready"}),
            ("taskrun_bootstrap", "taskrun_bootstrap_status", {"reached", "ready"}),
            ("phase_progression_stop_condition", "phase_progression_status", {"stop_condition_enforced", "skipped_due_to_prior_block", "ready"}),
        ]
        metrics: list[CoverageMetric] = []
        for domain, key, ready_values in checks:
            value = str(boundary.get(key) or "").casefold()
            if value in ready_values:
                coverage = 1.0
                gaps: list[str] = []
            elif value:
                coverage = 0.0
                gaps = [value]
            else:
                coverage = 0.5 if any(domain in stage.casefold() for stage in profile.expected_pipeline) else 0.0
                gaps = [key]
            metrics.append(self._metric(domain, coverage, "high", gaps))
        return metrics

    def _observer_backend_metrics(self, profile: FireTestProfile) -> list[CoverageMetric]:
        media = profile.metadata.get("media_metadata_capability") if isinstance(profile.metadata.get("media_metadata_capability"), dict) else {}
        if not media and not any(self._mentions_observer_backend(stage) for stage in profile.expected_pipeline):
            return []
        checks = [
            ("capability_registry", "capability_status", {"registered", "available", "ready"}),
            ("backend_configuration", "backend_status", {"available", "partial", "ready"}),
            ("observer_binding", "observer_binding_status", {"bound", "available", "ready"}),
            ("observer_execution", "execution_status", {"executed", "ready", "not_required"}),
            ("evidence_recording", "evidence_recording_status", {"recorded", "available", "ready"}),
            ("evidence_coverage", "evidence_coverage_status", {"sufficient", "complete", "ready"}),
        ]
        metrics: list[CoverageMetric] = []
        for domain, key, ready_values in checks:
            value = str(media.get(key) or "").casefold()
            if value in ready_values:
                coverage = 1.0
                gaps: list[str] = []
            elif value:
                coverage = 0.0
                gaps = [value]
            else:
                coverage = 0.5 if any(domain in stage.casefold() for stage in profile.expected_pipeline) else 0.0
                gaps = [key]
            metrics.append(self._metric(domain, coverage, "high", gaps))
        return metrics

    def _mentions_observer_backend(self, stage: str) -> bool:
        value = stage.casefold()
        return any(
            token in value
            for token in (
                "capability_registry",
                "backend",
                "observer_binding",
                "observer_execution",
                "evidence_recording",
                "evidence_coverage",
            )
        )

    def _relationship_cognition_metrics(self, profile: FireTestProfile) -> list[CoverageMetric]:
        relationship = profile.metadata.get("relationship_cognition") if isinstance(profile.metadata.get("relationship_cognition"), dict) else {}
        if not relationship and not any(self._mentions_relationship_cognition(stage) for stage in profile.expected_pipeline):
            return []
        checks = [
            ("relationship_capability", "capability_status", {"registered", "available", "ready"}),
            ("relationship_evidence", "evidence_status", {"sufficient", "partial", "available", "ready"}),
            ("relationship_provenance", "provenance_status", {"complete", "available", "ready"}),
            ("relationship_conflicts", "conflict_status", {"none", "resolved", "ready"}),
            ("relationship_confidence", "confidence_status", {"sufficient", "medium", "high", "ready"}),
            ("relationship_validation_policy", "validation_policy_status", {"available", "configured", "ready"}),
            ("relationship_ambiguity", "ambiguity_status", {"none", "resolved", "ready"}),
            ("relationship_validation", "validation_status", {"validation_ready", "validated", "not_required", "ready"}),
            ("relationship_truth_policy", "truth_policy_status", {"satisfied", "not_required", "ready"}),
        ]
        metrics: list[CoverageMetric] = []
        for domain, key, ready_values in checks:
            value = str(relationship.get(key) or "").casefold()
            if value in ready_values:
                coverage = 1.0
                gaps: list[str] = []
            elif value:
                coverage = 0.0
                gaps = [value]
            else:
                coverage = 0.5 if any(domain in stage.casefold() for stage in profile.expected_pipeline) else 0.0
                gaps = [key]
            metrics.append(self._metric(domain, coverage, "medium", gaps))
        return metrics

    def _mentions_relationship_cognition(self, stage: str) -> bool:
        value = stage.casefold()
        return any(token in value for token in ("relationship", "sidecar_candidate", "relationship_evidence"))

    def _semantic_maturity_metrics(self, profile: FireTestProfile) -> list[CoverageMetric]:
        maturity = profile.metadata.get("semantic_maturity") if isinstance(profile.metadata.get("semantic_maturity"), dict) else {}
        if not maturity and not any(self._mentions_semantic_maturity(stage) for stage in profile.expected_pipeline):
            return []
        checks = [
            ("evidence_availability", "evidence_availability", {"available", "sufficient", "ready"}),
            ("knowledge_availability", "knowledge_availability", {"available", "sufficient", "ready"}),
            ("semantic_completion", "semantic_completion", {"complete", "ready"}),
            ("truth_readiness", "truth_readiness", {"ready", "safe"}),
            ("validation_probability", "validation_probability", {"high", "likely", "ready"}),
        ]
        metrics: list[CoverageMetric] = []
        for domain, key, ready_values in checks:
            value = str(maturity.get(key) or "").casefold()
            if value in ready_values:
                coverage = 1.0
                gaps: list[str] = []
            elif value:
                coverage = 0.0
                gaps = [value]
            else:
                coverage = 0.5 if any(domain in stage.casefold() for stage in profile.expected_pipeline) else 0.0
                gaps = [key]
            metrics.append(self._metric(domain, coverage, "high", gaps))
        return metrics

    def _mentions_semantic_maturity(self, stage: str) -> bool:
        value = stage.casefold()
        return any(
            token in value
            for token in (
                "evidence_availability",
                "knowledge_availability",
                "semantic_completion",
                "truth_readiness",
                "semantic_coverage",
                "speaker_truth_readiness",
                "validation_probability",
            )
        )

    def _metric(self, domain: str, coverage: float, criticality: str, gaps: list[str]) -> CoverageMetric:
        health = "ready" if coverage >= 0.95 else "partial" if coverage > 0 else "blocked"
        return CoverageMetric(
            domain=domain,
            coverage=round(coverage, 4),
            confidence=1.0,
            health=health,
            criticality=criticality,  # type: ignore[arg-type]
            gaps=gaps,
            evidence_refs=[f"coverage:{domain}"],
        )

    def _ratio(self, observed: int, expected: int) -> float:
        if expected <= 0:
            return 1.0
        return max(0.0, min(1.0, observed / expected))


class CognitiveSimulationEngine:
    """Dry-run simulation over the declared cognitive pipeline."""

    def __init__(self, predictor: CognitiveGapPredictor | None = None, graph_service: CognitiveDependencyGraphService | None = None) -> None:
        self.predictor = predictor or CognitiveGapPredictor()
        self.graph_service = graph_service or CognitiveDependencyGraphService()

    def simulate(self, request: SimulationRequest) -> SimulationResult:
        graph = self.graph_service.build(request.profile)
        prediction = self.predictor.predict(
            request.profile,
            graph=graph,
            available_capabilities=request.available_capabilities,
        )
        blocked_component = prediction.probable_component if prediction.predicted_status == "blocked" else None
        steps: list[SimulationStep] = []
        failures: list[PredictedFailure] = []
        successes: list[PredictedSuccess] = []
        blocked_seen = False
        for index, component in enumerate(request.profile.expected_pipeline, start=1):
            component_token = component.casefold()
            step_capabilities = [
                capability
                for capability in request.profile.expected_capabilities
                if self._component_mentions_capability(component_token, capability)
            ]
            step_contracts = [
                contract
                for contract in request.profile.involved_contracts
                if self._component_mentions_contract(component_token, contract)
            ]
            should_block = not blocked_seen and blocked_component and self._component_matches(component_token, blocked_component)
            if should_block:
                failure = PredictedFailure(
                    component=component,
                    reason_code=prediction.reason_codes[0] if prediction.reason_codes else "PREDICTED_BLOCK",
                    summary=prediction.hypothesis,
                    confidence=prediction.confidence,
                    dependency_chain=prediction.dependency_chain,
                )
                failures.append(failure)
                steps.append(
                    SimulationStep(
                        index=index,
                        component=component,
                        status="predicted_blocked",
                        expected_contracts=step_contracts,
                        required_capabilities=step_capabilities,
                        reason_code=failure.reason_code,
                        explanation=failure.summary,
                        confidence=failure.confidence,
                    )
                )
                blocked_seen = True
                continue
            if blocked_seen:
                steps.append(
                    SimulationStep(
                        index=index,
                        component=component,
                        status="predicted_skipped",
                        expected_contracts=step_contracts,
                        required_capabilities=step_capabilities,
                        reason_code="UPSTREAM_PREDICTED_BLOCK",
                        explanation="Step skipped in simulation because an upstream boundary is predicted to block.",
                        confidence=prediction.confidence,
                    )
                )
                continue
            success = PredictedSuccess(
                component=component,
                summary="No declared blocker predicted for this component.",
                confidence=prediction.confidence,
                evidence_refs=[f"profile:{request.profile.profile_id}", f"component:{component}"],
            )
            successes.append(success)
            steps.append(
                SimulationStep(
                    index=index,
                    component=component,
                    status="predicted_success",
                    expected_contracts=step_contracts,
                    required_capabilities=step_capabilities,
                    explanation=success.summary,
                    confidence=success.confidence,
                )
            )
        status = "blocked" if failures else "ready"
        return SimulationResult(
            request_id=request.request_id,
            profile_id=request.profile.profile_id,
            status=status,
            steps=steps,
            predicted_failures=failures,
            predicted_successes=successes,
            confidence=prediction.confidence,
            summary=prediction.hypothesis,
        )

    def _component_matches(self, component: str, probable_component: str) -> bool:
        tokens = [token for token in probable_component.casefold().split("_") if token]
        return all(token in component for token in tokens) or probable_component.casefold() in component

    def _component_mentions_capability(self, component: str, capability: str) -> bool:
        tokens = [token for token in capability.casefold().replace("-", "_").split("_") if len(token) > 3]
        return any(token in component for token in tokens)

    def _component_mentions_contract(self, component: str, contract: str) -> bool:
        tokens = [token for token in contract.casefold().replace("-", "_").split("_") if len(token) > 3]
        return any(token in component for token in tokens)


class CVLReportWriter:
    """Writes CVL reports as analysis artifacts under reports/cvl."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PATHS.reports_root / "cvl"

    def write(
        self,
        *,
        suite: FireTestSuite,
        graphs: list[DependencyGraph],
        predictions: list[PredictionReport],
        coverage_reports: list[CoverageReport],
        simulations: list[SimulationResult],
    ) -> dict[str, str]:
        self.root.mkdir(parents=True, exist_ok=True)
        reports = {
            "firetest_lab": self._firetest_lab(suite),
            "prediction_report": self._prediction_report(predictions),
            "dependency_graph": self._dependency_graph(graphs),
            "coverage_report": self._coverage_report(coverage_reports),
            "simulation_report": self._simulation_report(simulations),
            "laboratory_summary": self._laboratory_summary(suite, predictions, coverage_reports, simulations),
        }
        paths: dict[str, str] = {}
        for name, content in reports.items():
            path = self.root / f"{name}.md"
            path.write_text(content, encoding="utf-8")
            paths[name] = str(path)
        return paths

    def _firetest_lab(self, suite: FireTestSuite) -> str:
        lines = ["# CVL - FireTest Laboratory", "", f"- Suite: `{suite.name}`", f"- Profiles: `{len(suite.profiles)}`", ""]
        for profile in suite.profiles:
            lines.extend(
                [
                    f"## {profile.name}",
                    "",
                    f"- Profile: `{profile.profile_id}`",
                    f"- Domain: `{profile.domain}`",
                    f"- Objective: {profile.objective}",
                    f"- Pipeline: `{', '.join(profile.expected_pipeline)}`",
                    f"- Contracts: `{', '.join(profile.involved_contracts)}`",
                    f"- Capabilities: `{', '.join(profile.expected_capabilities)}`",
                    f"- Artifacts: `{', '.join(profile.expected_artifacts)}`",
                    "",
                ]
            )
        return "\n".join(lines).strip() + "\n"

    def _prediction_report(self, predictions: list[PredictionReport]) -> str:
        lines = ["# CVL - Prediction Report", ""]
        for prediction in predictions:
            lines.extend(
                [
                    f"## {prediction.profile_id}",
                    "",
                    f"- Status: `{prediction.predicted_status}`",
                    f"- Probable component: `{prediction.probable_component or ''}`",
                    f"- Probable contract: `{prediction.probable_contract or ''}`",
                    f"- Probable capability: `{prediction.probable_capability or ''}`",
                    f"- Confidence: `{prediction.confidence}`",
                    f"- Reason codes: `{', '.join(prediction.reason_codes)}`",
                    f"- Hypothesis: {prediction.hypothesis}",
                    "",
                ]
            )
        return "\n".join(lines).strip() + "\n"

    def _dependency_graph(self, graphs: list[DependencyGraph]) -> str:
        lines = ["# CVL - Dependency Graph", ""]
        for graph in graphs:
            lines.extend(["## Graph", "", f"- Graph: `{graph.graph_id}`", f"- Profile: `{graph.source_profile_id or ''}`", ""])
            lines.extend(["| Node | Type | Depends On | Dependents |", "| --- | --- | --- | --- |"])
            for node in graph.nodes:
                lines.append(f"| `{node.node_id}` | `{node.node_type}` | `{', '.join(node.depends_on)}` | `{', '.join(node.dependents)}` |")
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    def _coverage_report(self, reports: list[CoverageReport]) -> str:
        lines = ["# CVL - Coverage Report", ""]
        for report in reports:
            lines.extend(["## Coverage", "", f"- Profile: `{report.profile_id or ''}`", f"- Overall: `{report.overall_coverage}`", f"- Status: `{report.overall_status}`", ""])
            lines.extend(["| Domain | Coverage | Health | Gaps |", "| --- | ---: | --- | --- |"])
            for metric in report.metrics:
                lines.append(f"| `{metric.domain}` | `{metric.coverage}` | `{metric.health}` | `{', '.join(metric.gaps)}` |")
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    def _simulation_report(self, simulations: list[SimulationResult]) -> str:
        lines = ["# CVL - Simulation Report", ""]
        for simulation in simulations:
            lines.extend(["## Simulation", "", f"- Profile: `{simulation.profile_id}`", f"- Status: `{simulation.status}`", f"- Confidence: `{simulation.confidence}`", f"- Summary: {simulation.summary}", ""])
            lines.extend(["| Step | Component | Status | Reason |", "| ---: | --- | --- | --- |"])
            for step in simulation.steps:
                lines.append(f"| {step.index} | `{step.component}` | `{step.status}` | `{step.reason_code or ''}` |")
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    def _laboratory_summary(
        self,
        suite: FireTestSuite,
        predictions: list[PredictionReport],
        coverage_reports: list[CoverageReport],
        simulations: list[SimulationResult],
    ) -> str:
        blocked = sum(1 for item in simulations if item.status == "blocked")
        avg_coverage = sum(item.overall_coverage for item in coverage_reports) / max(1, len(coverage_reports))
        lines = [
            "# CVL - Laboratory Summary",
            "",
            f"- Suite: `{suite.name}`",
            f"- Profiles: `{len(suite.profiles)}`",
            f"- Predictions: `{len(predictions)}`",
            f"- Simulations blocked: `{blocked}`",
            f"- Average cognitive coverage: `{round(avg_coverage, 4)}`",
            "",
            "## Principle",
            "",
            "A AIpinho compreende antes de agir.",
        ]
        return "\n".join(lines).strip() + "\n"


class CognitiveValidationLaboratoryService:
    """Facade for read-only CVL analysis.

    This is not a Runtime authority. It only composes CVL analyzers and writes
    reports from declared profiles and capability availability.
    """

    def __init__(
        self,
        *,
        laboratory: FireTestLaboratoryService | None = None,
        graph_service: CognitiveDependencyGraphService | None = None,
        predictor: CognitiveGapPredictor | None = None,
        coverage: CognitiveCoverageService | None = None,
        simulation: CognitiveSimulationEngine | None = None,
        writer: CVLReportWriter | None = None,
    ) -> None:
        self.laboratory = laboratory or FireTestLaboratoryService()
        self.graph_service = graph_service or CognitiveDependencyGraphService()
        self.predictor = predictor or CognitiveGapPredictor()
        self.coverage = coverage or CognitiveCoverageService()
        self.simulation = simulation or CognitiveSimulationEngine(predictor=self.predictor, graph_service=self.graph_service)
        self.writer = writer or CVLReportWriter()

    def analyze(
        self,
        profiles: list[FireTestProfile],
        *,
        suite_name: str = "cognitive_validation_suite",
        available_capabilities: list[str] | None = None,
        write_reports: bool = True,
    ) -> CognitiveValidationLaboratoryResult:
        suite = self.laboratory.suite(profiles, name=suite_name)
        graphs = [self.graph_service.build(profile) for profile in suite.profiles]
        graph_by_profile = {graph.source_profile_id: graph for graph in graphs}
        predictions = [
            self.predictor.predict(
                profile,
                graph=graph_by_profile.get(profile.profile_id),
                available_capabilities=available_capabilities,
            )
            for profile in suite.profiles
        ]
        coverage_reports = [
            self.coverage.report(profile, available_capabilities=available_capabilities)
            for profile in suite.profiles
        ]
        simulations = [
            self.simulation.simulate(
                SimulationRequest(profile=profile, available_capabilities=available_capabilities or [])
            )
            for profile in suite.profiles
        ]
        report_paths = (
            self.writer.write(
                suite=suite,
                graphs=graphs,
                predictions=predictions,
                coverage_reports=coverage_reports,
                simulations=simulations,
            )
            if write_reports
            else {}
        )
        status = "blocked" if any(item.status == "blocked" for item in simulations) else "ready"
        return CognitiveValidationLaboratoryResult(
            suite=suite,
            dependency_graphs=graphs,
            prediction_reports=predictions,
            coverage_reports=coverage_reports,
            simulation_results=simulations,
            report_paths=report_paths,
            status=status,
        )
