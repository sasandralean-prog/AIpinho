from __future__ import annotations

import re
import time
import unicodedata
from datetime import datetime, timezone
from typing import Any, Callable

from aipinho.capabilities.media_metadata import MediaMetadataObserverAdapter, media_metadata_capability_descriptor
from aipinho.capabilities.media_metadata.descriptor import MEDIA_METADATA_CANONICAL_KEYS, MEDIA_METADATA_EVIDENCE_KEYS
from aipinho.schemas.artifacts.contract_perception import (
    AttributeObservation,
    AttributeObservationRequirement,
    AttributeDescriptor,
    AttributeIdentityNormalizationTrace,
    CapabilityDecision,
    CapabilityMatch,
    CandidateEntity,
    CandidateEntitySet,
    ContractObservationPlan,
    ContractPerceptionResult,
    EvidenceRecord,
    EvidenceSet,
    KnowledgeRecord,
    ObservationCapability,
    ObservationGoal,
    ObservationPlan,
    ObservationStrategy,
    ObservationStrategyKind,
    ObservationTask,
    SemanticAssertion,
    SemanticCoverage,
    SemanticCoverage2,
    SemanticCoverageReport,
    SemanticQualityQuestion,
    SemanticSelfReview,
    SpecializationHypothesis,
)
from aipinho.schemas.artifacts.relationship import RelationshipGoal
from aipinho.services.artifacts.observation_execution_boundary_service import ObservationExecutionBoundaryService
from aipinho.services.artifacts.observed_entity_compilation_service import ObservedEntityCompilationService
from aipinho.services.artifacts.media_relationship_candidate_service import (
    MEDIA_RELATIONSHIP_CAPABILITY_ID,
    MediaRelationshipCandidateService,
)


class CapabilityRegistry:
    """Registry of generic observation capabilities.

    The registry is intentionally declarative. It does not choose strategies,
    execute observers, or infer domain facts; it only exposes capability
    metadata for the perception compiler.
    """

    def __init__(
        self,
        *,
        capabilities: dict[str, list[str] | dict[str, Any] | ObservationCapability] | list[ObservationCapability | dict[str, Any]] | None = None,
        fallback_attributes: list[str] | None = None,
    ) -> None:
        rows: list[ObservationCapability] = []
        if isinstance(capabilities, dict):
            for capability_id, payload in capabilities.items():
                rows.append(self._coerce_capability(str(capability_id), payload))
        elif isinstance(capabilities, list):
            for item in capabilities:
                rows.append(self._coerce_capability(None, item))
        if not rows and fallback_attributes:
            rows.append(
                ObservationCapability(
                    capability_id="observed_entity_attribute_reader",
                    name="Observed entity attribute reader",
                    version="1",
                    domain="observed_entity",
                    observable_attributes=sorted({self._normalize(attr) for attr in fallback_attributes if str(attr).strip()}),
                    compatible_entity_kinds=["*"],
                    supported_strategies=["read_existing_attribute"],
                    estimated_cost=0.0,
                    latency_ms=0,
                    typical_confidence=1.0,
                    limitations=["Reads attributes already present in the ObservedEntity graph."],
                    suggested_priority=0,
                    available=True,
                )
            )
            rows.append(
                ObservationCapability(
                    capability_id="file_path_attribute_extractor",
                    name="File path attribute extractor",
                    version="1",
                    domain="filesystem",
                    produces=["extension", "basename", "stem", "parent_path", "file_name"],
                    consumes=["relative_path", "name", "source_root"],
                    observable_attributes=["extension", "basename", "stem", "parent_path", "file_name"],
                    supported_attribute_names=["extension", "basename", "stem", "parent_path", "file_name"],
                    compatible_entity_kinds=["file"],
                    supported_entity_types=["file"],
                    evidence_types=["derived_path_attribute_evidence"],
                    preconditions=["source_path_or_name_available"],
                    supported_strategies=["calculate"],
                    estimated_cost=0.0,
                    latency_ms=0,
                    typical_confidence=1.0,
                    determinism="deterministic",
                    risk_level="low",
                    limitations=["Derives only generic path attributes from observed file path or name data."],
                    suggested_priority=1,
                    available=True,
                )
            )
            rows.append(media_metadata_capability_descriptor())
            rows.append(self._media_relationship_capability_descriptor())
        self._capabilities = {item.capability_id: self._normalize_capability(item) for item in rows}

    def capabilities(self) -> list[ObservationCapability]:
        return sorted(self._capabilities.values(), key=lambda item: (item.suggested_priority, item.capability_id))

    def matching_capabilities(
        self,
        *,
        attribute: str,
        entity_kinds: list[str],
        strategy_kind: ObservationStrategyKind | None = None,
    ) -> list[ObservationCapability]:
        canonical = self._normalize(attribute)
        normalized_kinds = {self._normalize(kind) for kind in entity_kinds if str(kind).strip()}
        matches: list[ObservationCapability] = []
        for capability in self._capabilities.values():
            if canonical not in capability.observable_attributes:
                continue
            if strategy_kind and strategy_kind not in capability.supported_strategies:
                continue
            compatible = set(capability.compatible_entity_kinds)
            if "*" not in compatible and normalized_kinds and compatible.isdisjoint(normalized_kinds):
                continue
            matches.append(capability)
        return sorted(matches, key=lambda item: (item.suggested_priority, item.capability_id))

    def relationship_capabilities(self) -> list[ObservationCapability]:
        return sorted(
            [
                item
                for item in self._capabilities.values()
                if "relationship_observation" in set(item.evidence_types)
                or "relationship_candidate" in set(item.produces)
            ],
            key=lambda item: (item.suggested_priority, item.capability_id),
        )

    def observers_for(self, attribute: str) -> list[str]:
        return [item.capability_id for item in self.matching_capabilities(attribute=attribute, entity_kinds=["*"])]

    def get(self, capability_id: str | None) -> ObservationCapability | None:
        if not capability_id:
            return None
        return self._capabilities.get(str(capability_id))

    def _coerce_capability(self, capability_id: str | None, payload: Any) -> ObservationCapability:
        if isinstance(payload, ObservationCapability):
            return payload
        if isinstance(payload, dict):
            data = dict(payload)
            data.setdefault("capability_id", capability_id or data.get("id") or f"capability_{len(data)}")
            data.setdefault("name", data["capability_id"])
            return ObservationCapability(**data)
        attributes = payload if isinstance(payload, list) else []
        return ObservationCapability(
            capability_id=capability_id or "capability",
            name=capability_id or "capability",
            observable_attributes=[self._normalize(attr) for attr in attributes if str(attr).strip()],
            compatible_entity_kinds=["*"],
            supported_strategies=["read_existing_attribute"],
            typical_confidence=1.0,
            available=True,
        )

    def _normalize_capability(self, capability: ObservationCapability) -> ObservationCapability:
        observable_attributes = {
            self._normalize(attr)
            for attr in [
                *capability.observable_attributes,
                *capability.supported_attribute_names,
                *capability.produces,
            ]
            if str(attr).strip()
        }
        compatible_entity_kinds = {
            self._normalize(kind) if kind != "*" else "*"
            for kind in [
                *capability.compatible_entity_kinds,
                *capability.supported_entity_types,
            ]
            if str(kind).strip()
        } or {"*"}
        available = capability.available and capability.status not in {"disabled", "unavailable", "blocked"}
        return capability.model_copy(
            update={
                "observable_attributes": sorted(observable_attributes),
                "supported_attribute_names": sorted(observable_attributes),
                "produces": sorted(observable_attributes),
                "compatible_entity_kinds": sorted(compatible_entity_kinds),
                "supported_entity_types": sorted(compatible_entity_kinds),
                "supported_strategies": list(dict.fromkeys(capability.supported_strategies)),
                "available": available,
            }
        )

    def _normalize(self, value: Any) -> str:
        normalized = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
        normalized = re.sub(r"[^0-9A-Za-z]+", "_", normalized.casefold())
        return "_".join(part for part in normalized.split("_") if part)

    def _media_relationship_capability_descriptor(self) -> ObservationCapability:
        return ObservationCapability(
            capability_id=MEDIA_RELATIONSHIP_CAPABILITY_ID,
            name="Media relationship candidate detector",
            version="1",
            domain="media_relationship",
            produces=["relationship_candidate", "relationship_evidence", "relationship_observation"],
            consumes=[
                "observed_entities",
                "entity_roles",
                "source_root_roles",
                "relationship_goal",
                "artifact_contract",
            ],
            observable_attributes=["relationship_candidate"],
            supported_attribute_names=["relationship_candidate"],
            compatible_entity_kinds=["file", "*"],
            supported_entity_types=["file"],
            evidence_types=["relationship_observation"],
            preconditions=[
                "observed_entities_available",
                "relationship_goal_available",
                "entity_role_available",
                "source_root_role_available",
                "capability_registry_active",
            ],
            supported_strategies=["combine_evidence"],
            estimated_cost=0.1,
            latency_ms=50,
            typical_confidence=0.62,
            confidence_profile={"minimum_candidate_confidence": 0.35, "single_signal_sufficient": False},
            determinism="deterministic",
            risk_level="low",
            requires_approval=False,
            observer_binding={"binding_type": "service_equivalent", "service": "MediaRelationshipCandidateService"},
            status="available",
            limitations=[
                "Produces candidates only; final relationship validation is out of scope.",
                "No single evidence signal is sufficient authority.",
            ],
            dependencies=["ObservedEntity", "RelationshipGoal", "CapabilityRegistry"],
            suggested_priority=8,
            available=True,
        )


ObserverCapabilityRegistry = CapabilityRegistry


class AttributeKeyNormalizer:
    """Builds stable attribute identities from contract labels.

    Human labels can be localized or corrupted by encoding boundaries. Runtime
    matching uses canonical keys; labels are preserved only for rendering and
    auditability.
    """

    def __init__(self, aliases: dict[str, list[str]] | None = None, display_labels: dict[str, str] | None = None) -> None:
        self.aliases = aliases or {}
        self.display_labels = display_labels or {}

    def descriptor(
        self,
        raw_label: Any,
        *,
        explicit: dict[str, Any] | None = None,
        locale: str | None = None,
        priority_notes: list[str] | None = None,
    ) -> AttributeDescriptor:
        raw = str(raw_label or "").strip()
        data = dict(explicit or {})
        explicit_key = str(data.get("canonical_key") or "").strip()
        canonical, notes = self.canonical_key(explicit_key or raw)
        raw_requiredness = str(data.get("requiredness") or data.get("required") or "required").casefold()
        requiredness = raw_requiredness if raw_requiredness in {"required", "optional", "nullable", "computed", "derived", "best_effort"} else "required"
        nullable = bool(data.get("nullable")) or requiredness == "nullable"
        evidence_required = bool(data.get("evidence_required", requiredness not in {"optional", "nullable", "best_effort"}))
        aliases = [self.normalize(item) for item in data.get("aliases") or [] if str(item).strip()]
        configured_display = self.display_labels.get(canonical)
        if data.get("display_label"):
            display_label = str(data.get("display_label"))
        elif configured_display and ("?" in raw or "\ufffd" in raw or not raw or self.normalize(raw) != canonical):
            display_label = configured_display
        else:
            display_label = raw or configured_display or canonical
        trace = self._trace(
            raw_label=raw,
            display_label=display_label,
            canonical_key=canonical,
            notes=notes,
        )
        return AttributeDescriptor(
            canonical_key=canonical,
            display_label=display_label,
            raw_label=raw,
            locale=str(data.get("locale") or locale or "") or None,
            semantic_type=str(data.get("semantic_type") or "contract_declared_attribute"),
            value_type=str(data.get("value_type") or "string"),
            requiredness=requiredness,  # type: ignore[arg-type]
            nullable=nullable,
            evidence_required=evidence_required,
            coverage_threshold=float(data.get("coverage_threshold") or 1.0),
            aliases=list(dict.fromkeys([*aliases, *self._aliases_for(canonical)])),
            normalization_notes=list(dict.fromkeys([*(priority_notes or []), *notes])),
            normalization_trace=trace,
        )

    def canonical_key(self, value: Any) -> tuple[str, list[str]]:
        normalized = self.normalize(value)
        notes = ["ascii_snake_case"]
        raw_text = str(value or "")
        if "?" in raw_text or "\ufffd" in raw_text:
            notes.append("lossy_or_replacement_character_present")
        for canonical, aliases in self.aliases.items():
            canonical_norm = self.normalize(canonical)
            alias_norms = {self.normalize(alias) for alias in aliases}
            if normalized == canonical_norm or normalized in alias_norms:
                if normalized != canonical_norm:
                    notes.append(f"matched_alias:{canonical_norm}")
                return canonical_norm, notes
        compact = self.compact(normalized)
        for canonical, aliases in self.aliases.items():
            canonical_norm = self.normalize(canonical)
            candidates = [canonical_norm, *(self.normalize(alias) for alias in aliases)]
            if any(self.compact(candidate) == compact for candidate in candidates):
                notes.append(f"matched_compact_alias:{canonical_norm}")
                return canonical_norm, notes
            if any(self._near_compact_match(compact, self.compact(candidate)) for candidate in candidates):
                notes.append(f"matched_near_alias:{canonical_norm}")
                return canonical_norm, notes
        return normalized, notes

    def normalize(self, value: Any) -> str:
        normalized = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
        normalized = re.sub(r"[^0-9A-Za-z]+", "_", normalized.casefold())
        return "_".join(part for part in normalized.split("_") if part)

    def compact(self, value: Any) -> str:
        return re.sub(r"[^0-9a-z]+", "", self.normalize(value))

    def _aliases_for(self, canonical_key: str) -> list[str]:
        aliases = self.aliases.get(canonical_key) or []
        return [self.normalize(item) for item in aliases if str(item).strip()]

    def _near_compact_match(self, value: str, candidate: str) -> bool:
        if not value or not candidate:
            return False
        limit = 2 if min(len(value), len(candidate)) >= 5 else 1
        if abs(len(value) - len(candidate)) > limit:
            return False
        return self._edit_distance(value, candidate, limit=limit) <= limit

    def _trace(
        self,
        *,
        raw_label: str,
        display_label: str,
        canonical_key: str,
        notes: list[str],
    ) -> AttributeIdentityNormalizationTrace:
        normalized = self.normalize(raw_label)
        mojibake = "?" in raw_label or "\ufffd" in raw_label
        alias_note = next((item for item in notes if item.startswith("matched_alias:")), None)
        compact_note = next((item for item in notes if item.startswith("matched_compact_alias:")), None)
        near_note = next((item for item in notes if item.startswith("matched_near_alias:")), None)
        if normalized == canonical_key and not mojibake:
            method = "exact"
            reason = "EXACT_CANONICAL_MATCH"
            confidence = 1.0
        elif alias_note:
            method = "known_alias"
            reason = "KNOWN_ALIAS_MATCH"
            confidence = 0.96
        elif compact_note:
            method = "compact_alias"
            reason = "MOJIBAKE_REPAIR_MATCH" if mojibake else "KNOWN_ALIAS_MATCH"
            confidence = 0.9
        elif near_note:
            method = "loss_tolerant_alias"
            reason = "LOSS_TOLERANT_ALIAS_MATCH"
            confidence = 0.82
        elif mojibake:
            method = "unresolved_mojibake"
            reason = "UNRESOLVED_ATTRIBUTE_LABEL"
            confidence = 0.3
        else:
            method = "normalized"
            reason = "EXACT_CANONICAL_MATCH" if normalized == canonical_key else "LOW_CONFIDENCE_LABEL_MATCH"
            confidence = 0.7 if normalized == canonical_key else 0.45
        alias_source = None
        for note in (alias_note, compact_note, near_note):
            if note:
                alias_source = note.split(":", 1)[1]
                break
        return AttributeIdentityNormalizationTrace(
            raw_label=raw_label,
            display_label=display_label,
            normalized_label=normalized,
            canonical_key=canonical_key,
            match_method=method,
            known_alias_source=alias_source,
            confidence=confidence,
            loss_tolerance_used=bool(near_note),
            mojibake_detected=mojibake,
            accepted=reason != "UNRESOLVED_ATTRIBUTE_LABEL",
            reason_code=reason,
        )

    def _edit_distance(self, left: str, right: str, *, limit: int) -> int:
        previous = list(range(len(right) + 1))
        for index, left_char in enumerate(left, start=1):
            current = [index]
            row_min = index
            for right_index, right_char in enumerate(right, start=1):
                cost = 0 if left_char == right_char else 1
                value = min(
                    previous[right_index] + 1,
                    current[right_index - 1] + 1,
                    previous[right_index - 1] + cost,
                )
                current.append(value)
                row_min = min(row_min, value)
            if row_min > limit:
                return row_min
            previous = current
        return previous[-1]


class ContractDrivenPerceptionService:
    """Compiles contract-driven perception IR from observed entities.

    The service does not render artifacts, validate task completion, or infer
    domain-specific facts. It only explains which observed entities can support
    a declared artifact contract and why attributes are or are not observable.
    """

    def __init__(
        self,
        *,
        observed_entities: ObservedEntityCompilationService | None = None,
        observer_registry: CapabilityRegistry | None = None,
        observation_boundary: ObservationExecutionBoundaryService | None = None,
        relationship_detector: MediaRelationshipCandidateService | None = None,
    ) -> None:
        self.observed_entities = observed_entities or ObservedEntityCompilationService()
        fallback_attributes = sorted(self.observed_entities.attribute_aliases)
        self.observer_registry = observer_registry or CapabilityRegistry(fallback_attributes=fallback_attributes)
        self.observation_boundary = observation_boundary or ObservationExecutionBoundaryService(
            adapters={"media_metadata_reader": MediaMetadataObserverAdapter()}
        )
        self.relationship_detector = relationship_detector or MediaRelationshipCandidateService()
        display_labels = self.observed_entities.policy.get("display_labels") if isinstance(self.observed_entities.policy.get("display_labels"), dict) else {}
        self.attribute_keys = AttributeKeyNormalizer(self.observed_entities.attribute_aliases, display_labels={str(k): str(v) for k, v in display_labels.items()})

    def compile(
        self,
        *,
        graph: dict[str, Any],
        declared_contract: dict[str, Any],
        stage_observer: Callable[[dict[str, Any]], None] | None = None,
    ) -> ContractPerceptionResult:
        compile_started = time.monotonic()
        trace: list[dict[str, Any]] = []
        metrics: dict[str, Any] = {}
        policy = self._compile_policy(declared_contract)

        self._append_compile_stage(
            trace,
            "before_compile_request_normalization",
            compile_started=compile_started,
            stage_observer=stage_observer,
            input_entity_count=self._graph_entity_count(graph),
        )
        declared_contract = dict(declared_contract or {})
        graph = dict(graph or {})
        metrics["input_entity_count"] = self._graph_entity_count(graph)
        metrics["declared_attribute_count"] = len([item for item in declared_contract.get("expected_schema") or [] if str(item).strip()])
        self._append_compile_stage(
            trace,
            "after_compile_request_normalization",
            compile_started=compile_started,
            stage_observer=stage_observer,
            **metrics,
        )

        self._append_compile_stage(trace, "before_requirement_resolution", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        plan = self.contract_observation_plan(declared_contract)
        metrics["required_attribute_count"] = len(plan.expected_attributes)
        metrics["relationship_requirement_count"] = len(plan.expected_relationships)
        self._append_compile_stage(trace, "after_requirement_resolution", compile_started=compile_started, stage_observer=stage_observer, **metrics)

        self._append_compile_stage(trace, "before_entity_projection", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        candidate_set = self.candidate_entity_set(graph=graph, plan=plan)
        selected_entities = self._selected_entities(graph, candidate_set)
        metrics.update(
            {
                "candidate_entity_count": len(candidate_set.candidates),
                "projected_entity_count": len(selected_entities),
                "semantic_gap_count": len(candidate_set.semantic_gaps),
            }
        )
        self._append_compile_stage(trace, "after_entity_projection", compile_started=compile_started, stage_observer=stage_observer, **metrics)

        self._append_compile_stage(trace, "before_relationship_projection", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        relationship_goal = self.relationship_goal(plan=plan, declared_contract=declared_contract)
        if policy["execute_relationship_detection"]:
            relationship_detection = self.relationship_observations(
                relationship_goal=relationship_goal,
                selected_entities=selected_entities,
                declared_contract=declared_contract,
            )
        else:
            relationship_detection = self._deferred_relationship_detection(relationship_goal)
        metrics["relationship_candidate_count"] = len(relationship_detection.get("candidates") or [])
        metrics["relationship_evidence_count"] = len(relationship_detection.get("evidence_records") or relationship_detection.get("evidence") or [])
        self._append_compile_stage(trace, "after_relationship_projection", compile_started=compile_started, stage_observer=stage_observer, **metrics)

        self._append_compile_stage(trace, "before_observation_binding", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        hypotheses = self.specialization_hypotheses(plan=plan, candidates=candidate_set.candidates)
        observation_plan = self.observation_plan(
            plan=plan,
            candidate_set=candidate_set,
            selected_entities=selected_entities,
            progress_observer=lambda stage, progress: self._append_compile_stage(
                trace,
                stage,
                compile_started=compile_started,
                stage_observer=stage_observer,
                **{**metrics, **progress},
            ),
        )
        metrics.update(
            {
                "observation_goal_count": len(observation_plan.observation_goals),
                "observation_task_count": len(observation_plan.observation_tasks),
                "capability_match_count": len(observation_plan.capability_matches),
            }
        )
        if policy["execute_observers"]:
            execution_results = self.execute_observation_tasks(
                observation_plan=observation_plan,
                selected_entities=selected_entities,
                max_executions=policy["max_observer_executions"],
            )
        else:
            execution_results = []
            observation_plan = self._mark_observer_execution_deferred(observation_plan)
        metrics["observation_execution_result_count"] = len(execution_results)
        observation_plan = self._apply_execution_evidence_to_plan(
            observation_plan=observation_plan,
            execution_results=execution_results,
        )
        self._append_compile_stage(trace, "after_observation_binding", compile_started=compile_started, stage_observer=stage_observer, **metrics)

        self._append_compile_stage(trace, "before_fact_projection", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        fact_projection_started = time.monotonic()
        self._append_compile_stage(trace, "before_fact_source_binding", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        self._append_compile_stage(trace, "before_source_index_build", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        source_indexes = self._fact_source_indexes(
            observation_plan=observation_plan,
            execution_results=execution_results,
        )
        metrics.update(source_indexes["metrics"])
        self._append_compile_stage(trace, "after_source_index_build", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        self._append_compile_stage(trace, "before_attribute_observation_projection", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        observations = self.attribute_observations(
            plan=plan,
            observation_plan=observation_plan,
            selected_entities=selected_entities,
            execution_results=execution_results,
            source_indexes=source_indexes,
            progress_observer=lambda stage, progress: self._append_compile_stage(
                trace,
                stage,
                compile_started=compile_started,
                stage_observer=stage_observer,
                **{**metrics, **progress},
            ),
        )
        metrics.update(self._attribute_observation_metrics(observations))
        self._append_compile_stage(trace, "after_attribute_observation_projection", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        self._append_compile_stage(trace, "before_evidence_ref_resolution", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        metrics.update(self._evidence_ref_metrics(observations))
        self._append_compile_stage(trace, "after_evidence_ref_resolution", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        self._append_compile_stage(trace, "before_evidence_set_materialization", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        evidence_set = self.evidence_set(
            observations=observations,
            execution_results=execution_results,
            relationship_evidence_records=relationship_detection.get("evidence_records", []),
            progress_observer=lambda stage, progress: self._append_compile_stage(
                trace,
                stage,
                compile_started=compile_started,
                stage_observer=stage_observer,
                **{**metrics, **progress},
            ),
        )
        metrics.update(self._evidence_set_metrics(evidence_set))
        self._append_compile_stage(trace, "after_evidence_set_materialization", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        self._append_compile_stage(trace, "before_source_provenance_binding", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        coverage = self.semantic_coverage(
            plan=plan,
            candidate_set=candidate_set,
            observation_plan=observation_plan,
            observations=observations,
        )
        coverage_report = self.semantic_coverage_report(
            plan=plan,
            candidate_set=candidate_set,
            observation_plan=observation_plan,
            observations=observations,
            coverage=coverage,
            evidence_set=evidence_set,
            declared_contract=declared_contract,
        )
        metrics["provenance_ref_count"] = self._provenance_ref_count(evidence_set)
        self._append_compile_stage(trace, "after_source_provenance_binding", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        self._append_compile_stage(trace, "before_source_binding_bound_check", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        metrics.update(
            {
                "attribute_observation_count": len(observations),
                "observations_in": len(observations),
                "evidence_record_count": len(evidence_set.records),
                "relationships_in": len(relationship_detection.get("candidates") or []),
                "facts_with_evidence_count": len([item for item in evidence_set.records if item.evidence_id]),
                "facts_with_provenance_count": len(
                    [
                        item
                        for item in evidence_set.records
                        if item.provenance or item.provenance_trace_id or item.raw_ref
                    ]
                ),
            }
        )
        source_binding_reason_code = self._source_binding_bound_reason(metrics=metrics, policy=policy)
        if source_binding_reason_code:
            metrics["reason_code"] = source_binding_reason_code
        self._append_compile_stage(trace, "after_source_binding_bound_check", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        self._append_compile_stage(trace, "fact_source_binding_completed", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        self._append_compile_stage(trace, "after_fact_source_binding", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        self._append_compile_stage(trace, "before_fact_candidate_projection", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        knowledge_records = self.knowledge_records(evidence_set=evidence_set)
        fact_kind_counts = self._fact_kind_counts(knowledge_records=knowledge_records, assertions=[])
        metrics.update(
            {
                "knowledge_record_count": len(knowledge_records),
                "observed_fact_count": fact_kind_counts["observed_fact_count"],
                "derived_fact_count": fact_kind_counts["derived_fact_count"],
                "candidate_fact_count": 0,
                "projected_fact_count": len(knowledge_records),
                "facts_with_evidence_count": len([item for item in knowledge_records if item.evidence_ids]),
                "facts_with_provenance_count": len([item for item in knowledge_records if item.provenance_refs or item.provenance]),
            }
        )
        self._append_compile_stage(trace, "after_fact_candidate_projection", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        self._append_compile_stage(trace, "before_fact_derivation", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        semantic_assertions = self.semantic_assertions(
            plan=plan,
            observation_plan=observation_plan,
            knowledge_records=knowledge_records,
            evidence_set=evidence_set,
        )
        fact_kind_counts = self._fact_kind_counts(knowledge_records=knowledge_records, assertions=semantic_assertions)
        metrics.update(
            {
                "semantic_assertion_count": len(semantic_assertions),
                "candidate_fact_count": fact_kind_counts["candidate_fact_count"],
                "observed_fact_count": fact_kind_counts["observed_fact_count"],
                "derived_fact_count": fact_kind_counts["derived_fact_count"],
                "projected_fact_count": len(knowledge_records) + len(semantic_assertions),
                "truth_eligible_count": len([item for item in semantic_assertions if item.truth_eligible]),
                "facts_with_evidence_count": len([item for item in knowledge_records if item.evidence_ids])
                + len([item for item in semantic_assertions if item.evidence_ids]),
                "facts_with_provenance_count": len([item for item in knowledge_records if item.provenance_refs or item.provenance])
                + len([item for item in semantic_assertions if item.provenance_refs or item.provenance]),
            }
        )
        self._append_compile_stage(trace, "fact_derivation_checkpoint", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        self._append_compile_stage(trace, "after_fact_derivation", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        self._append_compile_stage(trace, "before_fact_provenance_binding", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        semantic_self_review = self.semantic_self_review(
            plan=plan,
            observation_plan=observation_plan,
            evidence_set=evidence_set,
            knowledge_records=knowledge_records,
            assertions=semantic_assertions,
            coverage_report=coverage_report,
        )
        metrics["fact_provenance_issue_count"] = len(
            [
                item
                for item in semantic_self_review.questions
                if item.reason_code in {"TRACEABILITY_MISSING", "EVIDENCE_MISSING", "UNSUPPORTED_ASSERTION_PROMOTED"}
                and item.status == "fail"
            ]
        )
        self._append_compile_stage(trace, "after_fact_provenance_binding", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        self._append_compile_stage(trace, "before_fact_deduplication", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        semantic_coverage_2 = self.semantic_coverage_2(
            coverage_report=coverage_report,
            knowledge_records=knowledge_records,
            assertions=semantic_assertions,
            self_review=semantic_self_review,
        )
        metrics["deduplicated_fact_count"] = len(
            {
                (
                    item.subject_ref.get("entity_id") or item.subject_ref.get("artifact_id") or item.subject_ref.get("contract_id"),
                    item.canonical_key or item.attribute_name,
                    item.predicate,
                )
                for item in semantic_assertions
            }
        ) + len({(item.entity_ref.get("entity_id"), item.canonical_key or item.attribute_name) for item in knowledge_records})
        self._append_compile_stage(trace, "after_fact_deduplication", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        self._append_compile_stage(trace, "before_fact_validation_projection", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        fact_internal_reason_code = source_binding_reason_code or self._fact_projection_bound_reason(
            metrics=metrics,
            policy=policy,
            fact_projection_started=fact_projection_started,
        )
        if fact_internal_reason_code:
            metrics["reason_code"] = fact_internal_reason_code
            semantic_self_review, semantic_coverage_2 = self._apply_perception_block_reason(
                semantic_self_review=semantic_self_review,
                semantic_coverage_2=semantic_coverage_2,
                reason_code=fact_internal_reason_code,
            )
        metrics.update(
            {
                "fact_projection_elapsed_ms": round((time.monotonic() - fact_projection_started) * 1000, 3),
            }
        )
        self._append_compile_stage(trace, "after_fact_validation_projection", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        self._append_compile_stage(trace, "fact_projection_completed", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        self._append_compile_stage(trace, "after_fact_projection", compile_started=compile_started, stage_observer=stage_observer, **metrics)

        self._append_compile_stage(trace, "before_payload_assembly", compile_started=compile_started, stage_observer=stage_observer, **metrics)
        payload_metrics = self._perception_payload_metrics(
            trace=trace,
            metrics=metrics,
            policy=policy,
        )
        internal_reason_code = fact_internal_reason_code or self._payload_bound_reason(payload_metrics=payload_metrics, policy=policy)
        self._append_compile_stage(trace, "after_payload_assembly", compile_started=compile_started, stage_observer=stage_observer, **payload_metrics)
        self._append_compile_stage(trace, "before_payload_bound_check", compile_started=compile_started, stage_observer=stage_observer, **payload_metrics)
        if internal_reason_code:
            payload_metrics["bound_status"] = "blocked"
            payload_metrics["reason_code"] = internal_reason_code
            semantic_self_review, semantic_coverage_2 = self._apply_perception_block_reason(
                semantic_self_review=semantic_self_review,
                semantic_coverage_2=semantic_coverage_2,
                reason_code=internal_reason_code,
            )
        else:
            payload_metrics["bound_status"] = "within_bounds"
        self._append_compile_stage(trace, "after_payload_bound_check", compile_started=compile_started, stage_observer=stage_observer, **payload_metrics)
        self._append_compile_stage(trace, "perception_compile_completed", compile_started=compile_started, stage_observer=stage_observer, **payload_metrics)

        return ContractPerceptionResult(
            contract_observation_plan=plan,
            candidate_entity_set=candidate_set,
            specialization_hypotheses=hypotheses,
            observation_plan=observation_plan,
            observation_execution_results=execution_results,
            media_metadata_capability=self._media_metadata_capability_summary(execution_results),
            relationship_goal=relationship_goal,
            relationship_candidates=relationship_detection.get("candidates", []),
            relationship_evidence=relationship_detection.get("evidence", []),
            relationship_observations=relationship_detection.get("observations", []),
            relationship_provenance_traces=relationship_detection.get("provenance_traces", []),
            relationship_summary=self._relationship_summary(relationship_detection),
            attribute_observations=observations,
            evidence_set=evidence_set,
            knowledge_records=knowledge_records,
            semantic_assertions=semantic_assertions,
            semantic_self_review=semantic_self_review,
            semantic_coverage=coverage,
            semantic_coverage_report=coverage_report,
            semantic_coverage_2=semantic_coverage_2,
            compile_stage_trace=trace,
            payload_metrics=payload_metrics,
            compile_policy=self._public_compile_policy(policy),
            internal_reason_code=internal_reason_code,
        )

    def contract_observation_plan(self, declared_contract: dict[str, Any]) -> ContractObservationPlan:
        descriptors = self._attribute_descriptors(declared_contract)
        expected_attributes = [item.canonical_key for item in descriptors]
        priorities = {name: index for index, name in enumerate(expected_attributes)}
        selection_contract = self._entity_selection_contract(declared_contract)
        unbound: list[str] = []
        if not declared_contract.get("contract_id"):
            unbound.append("contract_id_not_declared")
        if not declared_contract.get("artifact_id") and not declared_contract.get("artifact_logical_path"):
            unbound.append("artifact_binding_not_declared")
        return ContractObservationPlan(
            contract_id=str(declared_contract.get("contract_id") or "") or None,
            artifact_id=str(declared_contract.get("artifact_id") or "") or None,
            artifact_logical_path=str(declared_contract.get("artifact_logical_path") or "") or None,
            artifact_kind=str(declared_contract.get("artifact_kind") or declared_contract.get("expected_kind") or "") or None,
            task_run_id=str(declared_contract.get("task_run_id") or "") or None,
            expected_kind=declared_contract.get("expected_kind"),
            expected_entities=list(declared_contract.get("expected_entities") or []),
            expected_relationships=list(declared_contract.get("expected_relationships") or []),
            expected_entity_role=selection_contract.get("expected_entity_role"),
            expected_entity_domain=selection_contract.get("expected_entity_domain"),
            allowed_root_roles=list(selection_contract.get("allowed_root_roles") or []),
            excluded_entity_roles=list(selection_contract.get("excluded_entity_roles") or []),
            entity_selection_contract=selection_contract,
            expected_attributes=list(dict.fromkeys(expected_attributes)),
            attribute_contracts=descriptors,
            expected_cardinality=dict(declared_contract.get("expected_cardinality") or {}),
            priorities=priorities,
            minimum_confidence=float(declared_contract.get("minimum_confidence") or 0.0),
            constraints={
                **dict(declared_contract.get("expected_semantics") or {}),
                "attribute_contracts_by_key": {item.canonical_key: item.model_dump(mode="json") for item in descriptors},
            },
            unbound_reason=";".join(unbound) if unbound else None,
        )

    def relationship_goal(
        self,
        *,
        plan: ContractObservationPlan,
        declared_contract: dict[str, Any],
    ) -> RelationshipGoal | None:
        relationship_contract = declared_contract.get("relationship_goal") if isinstance(declared_contract.get("relationship_goal"), dict) else {}
        expected_relationships = declared_contract.get("expected_relationships") if isinstance(declared_contract.get("expected_relationships"), list) else []
        relationship_semantics = declared_contract.get("relationship_semantics") if isinstance(declared_contract.get("relationship_semantics"), dict) else {}
        relationship_requested = bool(relationship_contract or expected_relationships or relationship_semantics.get("relationship_candidates_required"))
        if not relationship_requested:
            return None
        allowed = list(relationship_contract.get("allowed_relation_families") or relationship_semantics.get("allowed_relation_families") or [])
        required = list(relationship_contract.get("required_evidence_types") or relationship_semantics.get("required_evidence_types") or [])
        return RelationshipGoal(
            contract_id=plan.contract_id,
            artifact_id=plan.artifact_id,
            source_scope=dict(relationship_contract.get("source_scope") or {}),
            target_scope=dict(relationship_contract.get("target_scope") or {}),
            allowed_relation_families=[str(item) for item in allowed if str(item).strip()],
            required_evidence_types=[str(item) for item in required if str(item).strip()],
            forbidden_authority_shortcuts=list(
                relationship_contract.get("forbidden_authority_shortcuts")
                or [
                    "extension_as_final_authority",
                    "stem_similarity_as_final_authority",
                    "same_directory_as_final_authority",
                ]
            ),
            confidence_policy={
                "minimum_candidate_confidence": float(
                    relationship_contract.get("minimum_candidate_confidence")
                    or relationship_semantics.get("minimum_candidate_confidence")
                    or 0.35
                ),
                "single_signal_sufficient": False,
            },
            truth_policy={"truth_eligible": False, "validation_required": True},
            created_by=str(relationship_contract.get("created_by") or "declared_artifact_contract"),
        )

    def relationship_observations(
        self,
        *,
        relationship_goal: RelationshipGoal | None,
        selected_entities: list[dict[str, Any]],
        declared_contract: dict[str, Any],
    ) -> dict[str, Any]:
        if relationship_goal is None:
            return {
                "status": "not_available",
                "reason_codes": ["NO_RELATIONSHIP_GOAL"],
                "candidates": [],
                "evidence": [],
                "observations": [],
                "evidence_records": [],
                "coverage_summary": {
                    "candidate_count": 0,
                    "observation_count": 0,
                    "evidence_count": 0,
                    "truth_eligible": False,
                },
                "limitations": [],
            }
        capabilities = self.observer_registry.relationship_capabilities()
        capability = next((item for item in capabilities if item.capability_id == MEDIA_RELATIONSHIP_CAPABILITY_ID and item.available), None)
        if capability is None:
            return {
                "status": "blocked",
                "reason_codes": ["NO_MATCHING_RELATIONSHIP_CAPABILITY"],
                "candidates": [],
                "evidence": [],
                "observations": [],
                "evidence_records": [],
                "coverage_summary": {
                    "candidate_count": 0,
                    "observation_count": 0,
                    "evidence_count": 0,
                    "truth_eligible": False,
                },
                "limitations": ["relationship_capability_not_registered"],
            }
        missing_preconditions = self._relationship_capability_missing_preconditions(
            relationship_goal=relationship_goal,
            selected_entities=selected_entities,
        )
        if missing_preconditions:
            return {
                "status": "blocked",
                "capability_id": capability.capability_id,
                "reason_codes": missing_preconditions,
                "candidates": [],
                "evidence": [],
                "observations": [],
                "evidence_records": [],
                "coverage_summary": {
                    "candidate_count": 0,
                    "observation_count": 0,
                    "evidence_count": 0,
                    "truth_eligible": False,
                },
                "limitations": ["relationship_capability_precondition_failed"],
            }
        return self.relationship_detector.detect(
            entities=selected_entities,
            relationship_goal=relationship_goal,
            artifact_contract=declared_contract,
            producer_capability_id=capability.capability_id,
        )

    def _deferred_relationship_detection(self, relationship_goal: RelationshipGoal | None) -> dict[str, Any]:
        return {
            "status": "not_available" if relationship_goal is None else "deferred",
            "reason_codes": ["NO_RELATIONSHIP_GOAL"] if relationship_goal is None else ["RELATIONSHIP_PROJECTION_DEFERRED_BY_COMPILE_POLICY"],
            "candidates": [],
            "evidence": [],
            "evidence_records": [],
            "observations": [],
            "provenance_traces": [],
            "coverage_summary": {
                "candidate_count": 0,
                "observation_count": 0,
                "evidence_count": 0,
                "truth_eligible": False,
            },
            "limitations": [] if relationship_goal is None else ["relationship_projection_deferred_to_governed_observation_boundary"],
        }

    def _relationship_capability_missing_preconditions(
        self,
        *,
        relationship_goal: RelationshipGoal,
        selected_entities: list[dict[str, Any]],
    ) -> list[str]:
        missing: list[str] = []
        if relationship_goal is None:
            missing.append("NO_RELATIONSHIP_GOAL")
        if not selected_entities:
            missing.append("NO_OBSERVED_ENTITIES")
        if selected_entities and any(not str(entity.get("entity_role") or self._attribute_payload(entity, "entity_role").get("value") or "") for entity in selected_entities):
            missing.append("MISSING_ENTITY_ROLE")
        if selected_entities and any(not str(entity.get("source_root_role") or self._attribute_payload(entity, "source_root_role").get("value") or "") for entity in selected_entities):
            missing.append("MISSING_SOURCE_ROOT_ROLE")
        return list(dict.fromkeys(missing))

    def candidate_entity_set(self, *, graph: dict[str, Any], plan: ContractObservationPlan) -> CandidateEntitySet:
        rows = [item for item in graph.get("entities") or [] if isinstance(item, dict)]
        candidates: list[CandidateEntity] = []
        policy_not_applied = self._selection_policy_not_applied(graph=graph, plan=plan)
        for entity in rows:
            covered: list[str] = []
            potentially_observable: list[str] = []
            missing: list[str] = []
            entity_kind = str(entity.get("entity_kind") or "unknown")
            for attribute in plan.expected_attributes:
                value, present = self.observed_entities.value_for_field(entity, attribute)
                observers = [
                    item.capability_id
                    for item in self.observer_registry.matching_capabilities(
                        attribute=attribute,
                        entity_kinds=[entity_kind],
                    )
                ]
                if present and value not in (None, ""):
                    covered.append(attribute)
                elif observers:
                    potentially_observable.append(attribute)
                    missing.append(attribute)
                else:
                    missing.append(attribute)
            relevance = self._relevance(
                covered=covered,
                potentially_observable=potentially_observable,
                expected=plan.expected_attributes,
            )
            if relevance <= 0.0:
                continue
            policy_rejections = self._entity_policy_rejections(entity=entity, plan=plan)
            if policy_not_applied:
                policy_rejections.append("ENTITY_SELECTION_POLICY_NOT_APPLIED")
                policy_rejections = list(dict.fromkeys(policy_rejections))
            confidence = min(1.0, float(entity.get("confidence") or 0.0) * relevance)
            candidates.append(
                CandidateEntity(
                    entity_id=str(entity.get("entity_id") or ""),
                    entity_kind=entity_kind,
                    source=str(entity.get("source") or "") or None,
                    source_root_role=str(entity.get("source_root_role") or self._attribute_payload(entity, "source_root_role").get("value") or "") or None,
                    entity_role=str(entity.get("entity_role") or self._attribute_payload(entity, "entity_role").get("value") or "") or None,
                    entity_domain_hypotheses=list(entity.get("entity_domain_hypotheses") or []),
                    selection_eligibility=dict(entity.get("selection_eligibility") or {}),
                    exclusion_reasons=list(entity.get("exclusion_reasons") or []),
                    policy_rejection_reasons=policy_rejections,
                    confidence=confidence,
                    matching_reason="entity_attributes_overlap_declared_contract",
                    contract_relevance=relevance,
                    ambiguity_level=0.0,
                    covered_attributes=covered,
                    potentially_observable_attributes=potentially_observable,
                    missing_attributes=missing,
                    evidence_refs=[str(ref) for ref in entity.get("evidence_refs") or [] if ref],
                    status="rejected" if policy_rejections else "candidate",
                )
            )
        selected = self._select_candidates(candidates, plan=plan)
        selected_ids = {item.entity_id for item in selected}
        updated = [
            item.model_copy(update={"status": "rejected" if item.status == "rejected" else "selected" if item.entity_id in selected_ids else "candidate"})
            for item in candidates
        ]
        gaps = []
        if policy_not_applied:
            gaps.append(
                self._gap(
                    "ENTITY_SELECTION_POLICY_NOT_APPLIED",
                    reason_code="ENTITY_SELECTION_POLICY_NOT_APPLIED",
                    expected={
                        "selection_contract": "contract_specific_entity_policy",
                        "available_root_roles": graph.get("roots_scanned_by_role") or {},
                    },
                    observed=plan.entity_selection_contract,
                    domain="entity_selection_policy",
                    details={
                        "expected_kind": plan.expected_kind,
                        "allowed_root_roles": plan.allowed_root_roles,
                        "selection_mode": plan.entity_selection_contract.get("selection_mode"),
                    },
                )
            )
        if not updated:
            gaps.append(
                self._gap(
                    "CONTRACT_ENTITY_SELECTION_EMPTY",
                    reason_code="NO_ENTITY_OVERLAPS_CONTRACT_ATTRIBUTES",
                    expected=plan.expected_attributes,
                    observed="no_candidate_entities",
                    domain="entity_selection",
                )
            )
        elif not selected and any(item.status == "rejected" for item in updated):
            reasons = sorted({reason for item in updated for reason in item.policy_rejection_reasons})
            gaps.append(
                self._gap(
                    "ENTITY_SELECTION_EMPTY_FOR_CONTRACT",
                    reason_code=self._entity_selection_empty_reason(reasons),
                    expected=plan.entity_selection_contract,
                    observed={
                        "candidate_count": len(updated),
                        "rejected_count": len([item for item in updated if item.status == "rejected"]),
                        "rejection_reasons": reasons,
                    },
                    domain="entity_selection",
                )
            )
        return CandidateEntitySet(
            source_entity_set_id=str(graph.get("entity_set_id") or "") or None,
            contract_observation_plan_id=plan.plan_id,
            candidates=updated,
            selected_entity_ids=[item.entity_id for item in selected],
            semantic_gaps=gaps,
        )

    def _selection_policy_not_applied(self, *, graph: dict[str, Any], plan: ContractObservationPlan) -> bool:
        roots_by_role = graph.get("roots_scanned_by_role") if isinstance(graph.get("roots_scanned_by_role"), dict) else {}
        has_corpus_root = any(roots_by_role.get(role) for role in ("library_root", "corpus_root"))
        return bool(
            plan.expected_kind == "tabular_collection"
            and has_corpus_root
            and not plan.allowed_root_roles
            and plan.entity_selection_contract.get("selection_mode") == "generic_collection"
        )

    def _entity_selection_empty_reason(self, reasons: list[str]) -> str:
        reason_set = set(reasons)
        if "ENTITY_SELECTION_POLICY_NOT_APPLIED" in reason_set:
            return "ENTITY_SELECTION_POLICY_NOT_APPLIED"
        if "ROOT_ROLE_METADATA_MISSING" in reason_set:
            return "ROOT_ROLE_METADATA_MISSING"
        if "ENTITY_SELECTED_FROM_UNCLASSIFIED_ROOT" in reason_set:
            return "ENTITY_SELECTED_FROM_UNCLASSIFIED_ROOT"
        if "ROOT_ROLE_NOT_ALLOWED" in reason_set:
            return "WORKSPACE_ROLE_MISMATCH"
        return "ENTITY_INELIGIBLE_FOR_CONTRACT"

    def specialization_hypotheses(
        self,
        *,
        plan: ContractObservationPlan,
        candidates: list[CandidateEntity],
    ) -> list[SpecializationHypothesis]:
        labels = [
            self._normalize(str(item.get("declared_label") or item.get("entity_kind") or item.get("entity_role") or "contract_entity"))
            for item in plan.expected_entities
            if isinstance(item, dict)
        ] or ["contract_entity"]
        hypotheses: list[SpecializationHypothesis] = []
        for candidate in candidates:
            if candidate.status != "selected":
                continue
            for label in labels:
                hypotheses.append(
                    SpecializationHypothesis(
                        entity_id=candidate.entity_id,
                        base_entity_kind=candidate.entity_kind,
                        hypothesized_kind=label,
                        confidence=candidate.confidence,
                        matching_reason="hypothesis_derived_from_declared_contract_entity",
                        evidence_refs=candidate.evidence_refs,
                        accepted=candidate.confidence >= plan.minimum_confidence,
                    )
                )
        return hypotheses

    def observation_plan(
        self,
        *,
        plan: ContractObservationPlan,
        candidate_set: CandidateEntitySet,
        selected_entities: list[dict[str, Any]],
        progress_observer: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> ObservationPlan:
        def progress(stage: str, **items: Any) -> None:
            if progress_observer is None:
                return
            progress_observer(
                stage,
                {
                    "input_entity_count": len(candidate_set.candidates),
                    "projected_entity_count": len(candidate_set.selected_entity_ids),
                    "observation_requirement_count": len(plan.expected_attributes),
                    **items,
                },
            )

        progress("before_observation_goal_projection")
        goals = self.observation_goals(plan=plan, candidate_set=candidate_set, selected_entities=selected_entities)
        progress("after_observation_goal_projection", observation_goal_count=len(goals))
        progress("before_observation_strategy_projection", observation_goal_count=len(goals))
        strategies = self.observation_strategies(goals=goals, selected_entities=selected_entities)
        progress("after_observation_strategy_projection", observation_goal_count=len(goals), observation_strategy_count=len(strategies))
        progress("before_capability_match_projection", observation_goal_count=len(goals), observation_strategy_count=len(strategies))
        matches = self.capability_matches(goals=goals, strategies=strategies)
        progress(
            "after_capability_match_projection",
            observation_goal_count=len(goals),
            observation_strategy_count=len(strategies),
            capability_match_count=len(matches),
        )
        progress("before_capability_decision_projection", capability_match_count=len(matches))
        decisions = self.capability_decisions(goals=goals, matches=matches)
        progress("after_capability_decision_projection", capability_match_count=len(matches), capability_decision_count=len(decisions))
        progress("before_observation_task_projection", capability_decision_count=len(decisions))
        tasks = self.observation_tasks(goals=goals, strategies=strategies, decisions=decisions)
        progress("after_observation_task_projection", observation_task_count=len(tasks), capability_decision_count=len(decisions))
        progress("before_observation_requirement_projection", observation_task_count=len(tasks))
        decision_by_attribute = {self._goal_attribute(goals, item.goal_id): item for item in decisions}
        strategy_ids_by_goal = self._strategy_ids_by_goal(strategies)
        match_ids_by_goal = self._match_ids_by_goal(matches)
        requirements: list[AttributeObservationRequirement] = []
        gaps = list(candidate_set.semantic_gaps)
        for attribute in plan.expected_attributes:
            goal = next((item for item in goals if item.attribute_name == attribute), None)
            descriptor = self._descriptor_for(plan, attribute)
            decision = decision_by_attribute.get(attribute)
            observed_confidences = [
                float(self._attribute_payload(entity, attribute).get("confidence") or 0.0)
                for entity in selected_entities
                if self._attribute_payload(entity, attribute)
                and self._attribute_payload(entity, attribute).get("status") in {"observed", "inferred"}
                and self._attribute_payload(entity, attribute).get("value") not in (None, "")
            ]
            observed = bool(observed_confidences)
            confidence = max(observed_confidences) if observed_confidences else 0.0
            required = self._attribute_blocks_completion(descriptor)
            gap_reason = None
            explanation = None
            recommendation = None
            capability_ids = self._decision_capability_ids(decision, matches)
            if not observed and required:
                if not candidate_set.selected_entity_ids:
                    gap_reason = "ENTITY_SELECTION_EMPTY"
                    explanation = "No entity was selected as a reliable target for this observation goal."
                    recommendation = "Improve entity compilation or contract/entity overlap before observing attributes."
                elif decision and decision.reason_code:
                    gap_reason = decision.reason_code
                    explanation = decision.justification
                    recommendation = self._recommendation_for_gap_reason(gap_reason)
                else:
                    gap_reason = "ATTRIBUTE_VALUE_NOT_OBSERVED"
                    explanation = "A capability path exists, but no AttributeObservation value has been produced yet."
                    recommendation = "Execute the selected observer through the observer execution boundary."
                gaps.append(
                    self._gap(
                        f"ATTRIBUTE_NOT_OBSERVED:{attribute}",
                        reason_code=gap_reason,
                        expected=attribute,
                        observed="missing",
                        domain=self._domain_for_gap_reason(gap_reason),
                        evidence_refs=self._evidence_refs(selected_entities),
                        details={
                            "observation_goal_id": goal.goal_id if goal else None,
                            "capability_decision_id": decision.decision_id if decision else None,
                            "reason_chain": self._reason_chain(gap_reason),
                            "candidate_entity_count": len(candidate_set.candidates),
                            "selected_entity_count": len(candidate_set.selected_entity_ids),
                            "observer_capability_ids": capability_ids,
                            "strategy_ids": strategy_ids_by_goal.get(goal.goal_id if goal else "", []),
                            "capability_match_ids": match_ids_by_goal.get(goal.goal_id if goal else "", []),
                            "explanation": explanation,
                            "recommendation": recommendation,
                        },
                    )
                )
            requirements.append(
                AttributeObservationRequirement(
                    attribute_name=attribute,
                    canonical_key=descriptor.canonical_key if descriptor else attribute,
                    display_label=descriptor.display_label if descriptor else attribute,
                    raw_label=descriptor.raw_label if descriptor else attribute,
                    requiredness=descriptor.requiredness if descriptor else "required",
                    required=required,
                    nullable=bool(descriptor.nullable) if descriptor else False,
                    evidence_required=bool(descriptor.evidence_required) if descriptor else True,
                    observed=observed,
                    confidence=confidence,
                    priority=plan.priorities.get(attribute, 0),
                    observer_capability_ids=capability_ids,
                    observation_goal_id=goal.goal_id if goal else None,
                    strategy_ids=strategy_ids_by_goal.get(goal.goal_id if goal else "", []),
                    capability_match_ids=match_ids_by_goal.get(goal.goal_id if goal else "", []),
                    capability_decision_id=decision.decision_id if decision else None,
                    gap_reason=gap_reason,
                    explanation=explanation,
                    recommendation=recommendation,
                )
            )
        progress(
            "after_observation_requirement_projection",
            observation_goal_count=len(goals),
            observation_task_count=len(tasks),
            capability_match_count=len(matches),
            capability_decision_count=len(decisions),
            semantic_gap_count=len(gaps),
        )
        return ObservationPlan(
            contract_observation_plan_id=plan.plan_id,
            candidate_set_id=candidate_set.candidate_set_id,
            observation_goals=goals,
            observation_strategies=strategies,
            capability_matches=matches,
            capability_decisions=decisions,
            observation_tasks=tasks,
            requirements=requirements,
            semantic_gaps=gaps,
        )

    def observation_goals(
        self,
        *,
        plan: ContractObservationPlan,
        candidate_set: CandidateEntitySet,
        selected_entities: list[dict[str, Any]],
    ) -> list[ObservationGoal]:
        selected_kinds = sorted({str(entity.get("entity_kind") or "unknown") for entity in selected_entities})
        selected_roles = sorted({
            str(entity.get("entity_role") or self._attribute_payload(entity, "entity_role").get("value") or "")
            for entity in selected_entities
            if str(entity.get("entity_role") or self._attribute_payload(entity, "entity_role").get("value") or "")
        })
        selected_root_roles = sorted({
            str(entity.get("source_root_role") or self._attribute_payload(entity, "source_root_role").get("value") or "")
            for entity in selected_entities
            if str(entity.get("source_root_role") or self._attribute_payload(entity, "source_root_role").get("value") or "")
        })
        evidence_refs = self._evidence_refs(selected_entities)
        rows: list[ObservationGoal] = []
        for attribute in plan.expected_attributes:
            descriptor = self._descriptor_for(plan, attribute)
            rows.append(
                ObservationGoal(
                contract_id=plan.contract_id,
                artifact_id=plan.artifact_id,
                artifact_logical_path=plan.artifact_logical_path,
                artifact_kind=plan.artifact_kind,
                task_run_id=plan.task_run_id,
                entity_ref={
                    "entity_ids": list(candidate_set.selected_entity_ids),
                    "entity_kinds": selected_kinds,
                    "entity_roles": selected_roles,
                    "source_root_roles": selected_root_roles,
                    "file_path_available": any(self._entity_file_path(entity) for entity in selected_entities),
                },
                contract_observation_plan_id=plan.plan_id,
                attribute_name=attribute,
                canonical_key=descriptor.canonical_key if descriptor else attribute,
                display_label=descriptor.display_label if descriptor else attribute,
                raw_label=descriptor.raw_label if descriptor else attribute,
                attribute_contract=descriptor,
                expected_semantic_type=self._semantic_type_for_attribute(attribute, plan=plan),
                required_evidence_type=self._evidence_type_for_attribute(attribute, plan=plan),
                required_confidence=plan.minimum_confidence,
                required_coverage=descriptor.coverage_threshold if descriptor else 1.0,
                reason="declared_artifact_contract_requires_attribute",
                source_contract_ref={
                    "contract_id": plan.contract_id,
                    "artifact_id": plan.artifact_id,
                    "artifact_logical_path": plan.artifact_logical_path,
                    "plan_id": plan.plan_id,
                    "expected_kind": plan.expected_kind,
                    "expected_attribute": attribute,
                },
                target_entity_ids=list(candidate_set.selected_entity_ids),
                target_entity_kinds=selected_kinds,
                minimum_confidence=plan.minimum_confidence,
                importance=plan.priorities.get(attribute, 0),
                criticality=descriptor.requiredness if descriptor else "required",
                contract_origin={
                    "contract_id": plan.contract_id,
                    "artifact_id": plan.artifact_id,
                    "artifact_logical_path": plan.artifact_logical_path,
                    "expected_kind": plan.expected_kind,
                    "expected_attribute": attribute,
                },
                evidence_refs=evidence_refs,
                unbound_reason=plan.unbound_reason,
            )
            )
        return rows

    def observation_strategies(
        self,
        *,
        goals: list[ObservationGoal],
        selected_entities: list[dict[str, Any]],
    ) -> list[ObservationStrategy]:
        strategies: list[ObservationStrategy] = []
        for goal in goals:
            already_observed = any(
                self._attribute_payload(entity, goal.attribute_name).get("status") in {"observed", "inferred"}
                and self._attribute_payload(entity, goal.attribute_name).get("value") not in (None, "")
                for entity in selected_entities
            )
            for kind in self._strategy_kinds_for_goal(already_observed=already_observed):
                required_preconditions = self._strategy_prerequisites(kind)
                satisfied_preconditions = self._satisfied_strategy_preconditions(
                    kind=kind,
                    goal=goal,
                    selected_entities=selected_entities,
                    already_observed=already_observed,
                )
                missing_preconditions = [
                    item for item in required_preconditions if item not in set(satisfied_preconditions)
                ]
                strategies.append(
                    ObservationStrategy(
                        goal_id=goal.goal_id,
                        contract_id=goal.contract_id,
                        artifact_id=goal.artifact_id,
                        artifact_logical_path=goal.artifact_logical_path,
                        artifact_kind=goal.artifact_kind,
                        task_run_id=goal.task_run_id,
                        strategy_kind=kind,
                        strategy_type=kind,
                        attribute_name=goal.attribute_name,
                        canonical_key=goal.canonical_key,
                        display_label=goal.display_label,
                        target_entity_ids=goal.target_entity_ids,
                        required_capability_kind=self._capability_kind_for_strategy(kind),
                        candidate_capability_tags=[self._capability_kind_for_strategy(kind), goal.attribute_name],
                        required_inputs=required_preconditions,
                        required_attributes=[goal.attribute_name],
                        prerequisites=required_preconditions,
                        preconditions=required_preconditions,
                        required_preconditions=required_preconditions,
                        satisfied_preconditions=satisfied_preconditions,
                        missing_preconditions=missing_preconditions,
                        expected_outputs=[goal.attribute_name],
                        evidence_types=[goal.required_evidence_type or "structured_attribute_evidence"],
                        estimated_cost=self._strategy_cost(kind),
                        estimated_latency_ms=self._strategy_latency(kind),
                        estimated_latency=self._strategy_latency(kind),
                        expected_confidence=1.0 if kind == "read_existing_attribute" and already_observed else 0.5,
                        estimated_confidence=1.0 if kind == "read_existing_attribute" and already_observed else 0.5,
                        deterministic=kind in {"read_existing_attribute", "calculate", "combine_evidence"},
                        limitations=self._strategy_limitations(kind),
                        risk_level="low" if kind == "read_existing_attribute" else "medium",
                        rationale=self._strategy_rationale(kind),
                    )
                )
        return strategies

    def capability_matches(
        self,
        *,
        goals: list[ObservationGoal],
        strategies: list[ObservationStrategy],
    ) -> list[CapabilityMatch]:
        goal_by_id = {item.goal_id: item for item in goals}
        matches: list[CapabilityMatch] = []
        for strategy in strategies:
            goal = goal_by_id.get(strategy.goal_id)
            if not goal:
                continue
            candidates = self.observer_registry.matching_capabilities(
                attribute=goal.attribute_name,
                entity_kinds=goal.target_entity_kinds or ["*"],
                strategy_kind=strategy.strategy_kind,
            )
            if not candidates:
                matches.append(self._negative_capability_match(goal=goal, strategy=strategy))
                continue
            for capability in candidates:
                match = self._score_capability_match(goal=goal, strategy=strategy, capability=capability)
                matches.append(match)
        return matches

    def capability_decisions(
        self,
        *,
        goals: list[ObservationGoal],
        matches: list[CapabilityMatch],
    ) -> list[CapabilityDecision]:
        decisions: list[CapabilityDecision] = []
        matches_by_goal: dict[str, list[CapabilityMatch]] = {}
        for match in matches:
            matches_by_goal.setdefault(match.goal_id, []).append(match)
        for goal in goals:
            goal_matches = sorted(matches_by_goal.get(goal.goal_id, []), key=lambda item: item.score, reverse=True)
            available_matches = [
                item
                for item in goal_matches
                if item.match_status == "MATCHED"
                and item.capability_id
                and item.available
                and not item.conflicts
                and not item.missing_preconditions
            ]
            if not goal_matches:
                decisions.append(
                    CapabilityDecision(
                        goal_id=goal.goal_id,
                        contract_id=goal.contract_id,
                        artifact_id=goal.artifact_id,
                        artifact_logical_path=goal.artifact_logical_path,
                        artifact_kind=goal.artifact_kind,
                        task_run_id=goal.task_run_id,
                        status="no_matching_capability",
                        decision_status="BLOCKED_NO_CAPABILITY",
                        decision_reason="no registered capability matched this observation goal",
                        justification="No registered capability supports the required attribute, entity compatibility, and observation strategy.",
                        score=0.0,
                        criteria=self._arbitration_criteria(),
                        reason_code="NO_MATCHING_CAPABILITY",
                        evidence_refs=goal.evidence_refs,
                        candidate_capability_ids=[],
                        confidence=0.0,
                        coverage=0.0,
                        blocking_reason="NO_MATCHING_CAPABILITY",
                    )
                )
                continue
            if all(item.match_status == "NO_MATCHING_CAPABILITY" for item in goal_matches):
                decisions.append(
                    CapabilityDecision(
                        goal_id=goal.goal_id,
                        contract_id=goal.contract_id,
                        artifact_id=goal.artifact_id,
                        artifact_logical_path=goal.artifact_logical_path,
                        artifact_kind=goal.artifact_kind,
                        task_run_id=goal.task_run_id,
                        status="no_matching_capability",
                        decision_status="BLOCKED_NO_CAPABILITY",
                        decision_reason="matching was attempted and no registered capability matched this observation goal",
                        selected_strategy_id=goal_matches[0].strategy_id,
                        justification="No registered capability supports the required attribute, entity compatibility, and observation strategy.",
                        rejected_alternatives=[self._match_summary(item) for item in goal_matches],
                        score=0.0,
                        criteria=self._arbitration_criteria(),
                        reason_code="NO_MATCHING_CAPABILITY",
                        evidence_refs=goal.evidence_refs,
                        candidate_capability_ids=[],
                        confidence=0.0,
                        coverage=0.0,
                        blocking_reason="NO_MATCHING_CAPABILITY",
                    )
                )
                continue
            if not available_matches:
                decisions.append(
                    CapabilityDecision(
                        goal_id=goal.goal_id,
                        contract_id=goal.contract_id,
                        artifact_id=goal.artifact_id,
                        artifact_logical_path=goal.artifact_logical_path,
                        artifact_kind=goal.artifact_kind,
                        task_run_id=goal.task_run_id,
                        status="capability_rejected",
                        decision_status="BLOCKED_PRECONDITION",
                        decision_reason="matched capabilities were rejected by availability or conflicts",
                        justification="Capabilities matched the attribute but were rejected by availability or conflict criteria.",
                        rejected_alternatives=[self._match_summary(item) for item in goal_matches],
                        score=max(item.score for item in goal_matches),
                        criteria=self._arbitration_criteria(),
                        reason_code="CAPABILITY_REJECTED",
                        evidence_refs=goal.evidence_refs,
                        candidate_capability_ids=[item.capability_id for item in goal_matches if item.capability_id],
                        confidence=max(item.confidence_score for item in goal_matches),
                        coverage=max(item.coverage_score for item in goal_matches),
                        blocking_reason="CAPABILITY_REJECTED",
                    )
                )
                continue
            best = available_matches[0]
            tied = [item for item in available_matches if item.score == best.score]
            if len(tied) > 1:
                decisions.append(
                    CapabilityDecision(
                        goal_id=goal.goal_id,
                        contract_id=goal.contract_id,
                        artifact_id=goal.artifact_id,
                        artifact_logical_path=goal.artifact_logical_path,
                        artifact_kind=goal.artifact_kind,
                        task_run_id=goal.task_run_id,
                        status="multiple_capabilities_available",
                        decision_status="BLOCKED_AMBIGUOUS",
                        decision_reason="multiple capabilities received the same top arbitration score",
                        justification="Multiple capabilities have equivalent arbitration score for this observation goal.",
                        rejected_alternatives=[self._match_summary(item) for item in tied],
                        score=best.score,
                        criteria=self._arbitration_criteria(),
                        reason_code="MULTIPLE_CAPABILITIES_AVAILABLE",
                        evidence_refs=goal.evidence_refs,
                        candidate_capability_ids=[item.capability_id for item in available_matches],
                        confidence=best.confidence_score,
                        coverage=best.coverage_score,
                        cost=best.score,
                        blocking_reason="MULTIPLE_CAPABILITIES_AVAILABLE",
                    )
                )
                continue
            if best.score < goal.minimum_confidence:
                decisions.append(
                    CapabilityDecision(
                        goal_id=goal.goal_id,
                        contract_id=goal.contract_id,
                        artifact_id=goal.artifact_id,
                        artifact_logical_path=goal.artifact_logical_path,
                        artifact_kind=goal.artifact_kind,
                        task_run_id=goal.task_run_id,
                        status="low_confidence",
                        decision_status="BLOCKED_PRECONDITION",
                        decision_reason="best capability did not satisfy confidence requirements",
                        selected_capability_id=best.capability_id,
                        selected_strategy_id=best.strategy_id,
                        justification="Best capability did not satisfy the minimum confidence required by the contract.",
                        rejected_alternatives=[self._match_summary(item) for item in available_matches[1:]],
                        score=best.score,
                        criteria=self._arbitration_criteria(),
                        reason_code="LOW_CONFIDENCE",
                        evidence_refs=goal.evidence_refs,
                        candidate_capability_ids=[item.capability_id for item in available_matches],
                        confidence=best.confidence_score,
                        coverage=best.coverage_score,
                        blocking_reason="LOW_CONFIDENCE",
                    )
                )
                continue
            decisions.append(
                CapabilityDecision(
                    goal_id=goal.goal_id,
                    contract_id=goal.contract_id,
                    artifact_id=goal.artifact_id,
                    artifact_logical_path=goal.artifact_logical_path,
                    artifact_kind=goal.artifact_kind,
                    task_run_id=goal.task_run_id,
                    status="selected",
                    decision_status="SELECTED",
                    decision_reason="capability selected by generic arbitration criteria",
                    selected_capability_id=best.capability_id,
                    selected_strategy_id=best.strategy_id,
                    justification="Capability selected by contract coverage, entity compatibility, confidence, cost, latency, availability, and determinism.",
                    rejected_alternatives=[self._match_summary(item) for item in available_matches[1:]],
                    score=best.score,
                    criteria=self._arbitration_criteria(),
                    evidence_refs=goal.evidence_refs,
                    candidate_capability_ids=[item.capability_id for item in available_matches],
                    confidence=best.confidence_score,
                    coverage=best.coverage_score,
                    cost=best.score,
                    determinism="deterministic",
                )
            )
        return decisions

    def observation_tasks(
        self,
        *,
        goals: list[ObservationGoal],
        strategies: list[ObservationStrategy],
        decisions: list[CapabilityDecision],
    ) -> list[ObservationTask]:
        strategy_by_id = {item.strategy_id: item for item in strategies}
        goal_by_id = {item.goal_id: item for item in goals}
        tasks: list[ObservationTask] = []
        for decision in decisions:
            goal = goal_by_id.get(decision.goal_id)
            if goal is None:
                continue
            strategy = strategy_by_id.get(decision.selected_strategy_id or "")
            if decision.reason_code == "NO_MATCHING_CAPABILITY":
                status = "BLOCKED_NO_CAPABILITY"
            elif decision.status == "selected":
                status = "READY_FOR_OBSERVER"
            else:
                status = "PLANNED"
            tasks.append(
                ObservationTask(
                    goal_id=goal.goal_id,
                    contract_id=goal.contract_id,
                    artifact_id=goal.artifact_id,
                    artifact_logical_path=goal.artifact_logical_path,
                    artifact_kind=goal.artifact_kind,
                    task_run_id=goal.task_run_id,
                    strategy_id=strategy.strategy_id if strategy else None,
                    capability_id=decision.selected_capability_id,
                    entity_ref=goal.entity_ref,
                    attribute_name=goal.attribute_name,
                    canonical_key=goal.canonical_key,
                    inputs={
                        "target_entity_ids": goal.target_entity_ids,
                        "target_entity_kinds": goal.target_entity_kinds,
                        "required_confidence": goal.required_confidence,
                    },
                    expected_outputs=[goal.attribute_name],
                    expected_evidence=[goal.required_evidence_type or "structured_attribute_evidence"],
                    status=status,
                    created_from={
                        "observation_goal_id": goal.goal_id,
                        "capability_decision_id": decision.decision_id,
                        "reason_code": decision.reason_code,
                    },
                )
            )
        return tasks

    def attribute_observations(
        self,
        *,
        plan: ContractObservationPlan,
        observation_plan: ObservationPlan,
        selected_entities: list[dict[str, Any]],
        execution_results: list[Any] | None = None,
        source_indexes: dict[str, Any] | None = None,
        progress_observer: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> list[AttributeObservation]:
        observed_at = datetime.now(timezone.utc).isoformat()
        rows: list[AttributeObservation] = []
        indexes = source_indexes or self._fact_source_indexes(
            observation_plan=observation_plan,
            execution_results=execution_results,
        )
        requirement_by_attribute = indexes["requirement_by_attribute"]
        decision_by_id = indexes["decision_by_id"]
        capability_by_id = indexes["capability_by_id"]
        execution_evidence = indexes["execution_evidence_by_entity_attribute"]
        attempted = 0
        checkpoint_interval = max(1, int(indexes["policy"].get("attribute_projection_checkpoint_interval") or 250))
        for entity_index, entity in enumerate(selected_entities, start=1):
            entity_id = str(entity.get("entity_id") or "")
            for attribute in plan.expected_attributes:
                attempted += 1
                payload = self._attribute_payload(entity, attribute)
                requirement = requirement_by_attribute.get(attribute)
                decision = decision_by_id.get(requirement.capability_decision_id if requirement else None)
                capability = capability_by_id.get(decision.selected_capability_id if decision else None)
                selected_strategy_id = decision.selected_strategy_id if decision else None
                canonical = self.observed_entities.canonical_attribute_name(attribute)
                evidence_record = execution_evidence.get((entity_id, canonical))
                if evidence_record is not None:
                    rows.append(
                        AttributeObservation(
                            entity_id=entity_id,
                            attribute_name=attribute,
                            canonical_key=canonical,
                            observed_value=evidence_record.normalized_value,
                            confidence=evidence_record.confidence,
                            evidence_refs=[evidence_record.evidence_id],
                            observer_id=evidence_record.observer_id,
                            observer_version=str((evidence_record.provenance or {}).get("observer_version") or "") or None,
                            capability_id=evidence_record.capability_id,
                            strategy_id=selected_strategy_id,
                            acquisition_method=evidence_record.acquisition_method,
                            observation_method="execute_observer",
                            execution_duration=None,
                            evidence={"evidence_record_id": evidence_record.evidence_id},
                            provenance={
                                **dict(evidence_record.provenance or {}),
                                "source": "observation_execution_boundary",
                                "observation_goal_id": requirement.observation_goal_id if requirement else None,
                                "capability_decision_id": requirement.capability_decision_id if requirement else None,
                            },
                            timestamp=evidence_record.timestamp or observed_at,
                            ambiguity=evidence_record.ambiguity,
                            observation_state="observed",
                        )
                    )
                    continue
                if payload and payload.get("status") in {"observed", "inferred"} and payload.get("value") not in (None, ""):
                    rows.append(
                        AttributeObservation(
                            entity_id=entity_id,
                            attribute_name=attribute,
                            canonical_key=attribute,
                            observed_value=payload.get("value"),
                            confidence=float(payload.get("confidence") or 1.0),
                            evidence_refs=[str(ref) for ref in payload.get("evidence_refs") or [] if ref],
                            observer_id=capability.capability_id if capability else "observed_entity_attribute_reader",
                            observer_version=capability.version if capability else "1",
                            capability_id=capability.capability_id if capability else "observed_entity_attribute_reader",
                            strategy_id=selected_strategy_id,
                            acquisition_method="read_existing_attribute",
                            observation_method="read_existing_attribute",
                            execution_duration=0.0,
                            evidence={"attribute_payload": payload},
                            provenance={
                                "source": "observed_entity_graph",
                                "observation_goal_id": requirement.observation_goal_id if requirement else None,
                                "capability_decision_id": requirement.capability_decision_id if requirement else None,
                            },
                            timestamp=observed_at,
                            observation_state="observed",
                        )
                    )
                    continue
                derived = self._derive_file_path_attribute(entity=entity, attribute=attribute)
                if derived is not None and capability and capability.capability_id == "file_path_attribute_extractor":
                    rows.append(
                        AttributeObservation(
                            entity_id=entity_id,
                            attribute_name=attribute,
                            canonical_key=attribute,
                            observed_value=derived,
                            confidence=1.0,
                            evidence_refs=[str(ref) for ref in entity.get("evidence_refs") or [] if ref],
                            observer_id=capability.capability_id,
                            observer_version=capability.version,
                            capability_id=capability.capability_id,
                            strategy_id=selected_strategy_id,
                            acquisition_method="derive_from_path",
                            observation_method="calculate",
                            execution_duration=0.0,
                            evidence={"derived_from": "observed_file_path_attributes"},
                            provenance={
                                "source": "observed_entity_graph",
                                "observation_goal_id": requirement.observation_goal_id if requirement else None,
                                "capability_decision_id": requirement.capability_decision_id if requirement else None,
                                "derivation": "path_attribute",
                            },
                            timestamp=observed_at,
                            observation_state="observed",
                        )
                    )
                    continue
                rows.append(
                        AttributeObservation(
                            entity_id=entity_id,
                            attribute_name=attribute,
                            canonical_key=attribute,
                            confidence=0.0,
                            evidence_refs=[str(ref) for ref in entity.get("evidence_refs") or [] if ref],
                            observer_id=capability.capability_id if capability else None,
                            observer_version=capability.version if capability else None,
                            capability_id=capability.capability_id if capability else None,
                            strategy_id=selected_strategy_id,
                            acquisition_method="capability_selected_pending_execution" if capability else "capability_matching",
                            observation_method=self._strategy_kind_for_id(observation_plan.observation_strategies, selected_strategy_id),
                            execution_duration=None,
                            evidence={},
                            provenance={
                                "source": "contract_driven_perception",
                                "observation_goal_id": requirement.observation_goal_id if requirement else None,
                                "capability_decision_id": requirement.capability_decision_id if requirement else None,
                                "reason_code": requirement.gap_reason if requirement else None,
                            },
                            timestamp=observed_at,
                            observation_state="missing" if capability else "unsupported",
                        )
                )
            if progress_observer is not None and (entity_index % checkpoint_interval == 0 or entity_index == len(selected_entities)):
                progress_observer(
                    "attribute_observation_projection_checkpoint",
                    {
                        "entity_count": len(selected_entities),
                        "source_entity_processed_count": entity_index,
                        "observation_requirement_count": len(plan.expected_attributes),
                        "attribute_observation_attempt_count": attempted,
                        "attribute_observation_count": len(rows),
                        **self._attribute_observation_metrics(rows),
                    },
                )
        return rows

    def evidence_set(
        self,
        *,
        observations: list[AttributeObservation],
        execution_results: list[Any] | None = None,
        relationship_evidence_records: list[EvidenceRecord] | None = None,
        progress_observer: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> EvidenceSet:
        records: list[EvidenceRecord] = []
        seen_execution_ids: set[str] = set()
        for result in execution_results or []:
            evidence_set = getattr(result, "evidence_set", None)
            for record in getattr(evidence_set, "records", []) or []:
                if record.evidence_id in seen_execution_ids:
                    continue
                records.append(record)
                seen_execution_ids.add(record.evidence_id)
        materialized = 0
        checkpoint_interval = 500
        for index, observation in enumerate(observations, start=1):
            if observation.observation_state != "observed":
                continue
            if observation.evidence_refs and any(ref in seen_execution_ids for ref in observation.evidence_refs):
                continue
            records.append(
                EvidenceRecord(
                    source=(observation.provenance or {}).get("source") or "contract_driven_perception",
                    acquisition_method=observation.acquisition_method,
                    observer_id=observation.observer_id,
                    capability_id=observation.capability_id,
                    entity_ref={"entity_id": observation.entity_id},
                    attribute_name=observation.attribute_name,
                    canonical_key=observation.canonical_key or observation.attribute_name,
                    raw_ref=(observation.evidence_refs or [None])[0],
                    normalized_value=observation.observed_value,
                    semantic_type=None,
                    confidence=observation.confidence,
                    provenance=observation.provenance,
                    timestamp=observation.timestamp,
                    ambiguity=observation.ambiguity,
                    limitations=[],
                )
            )
            materialized += 1
            if progress_observer is not None and (materialized % checkpoint_interval == 0 or index == len(observations)):
                progress_observer(
                    "evidence_set_materialization_checkpoint",
                    {
                        "attribute_observation_count": len(observations),
                        "evidence_record_count": len(records),
                        "evidence_record_materialized_count": materialized,
                        "evidence_ref_count": len({ref for item in observations for ref in item.evidence_refs}),
                    },
                )
        records.extend(relationship_evidence_records or [])
        attribute_names = sorted({item.attribute_name for item in records if item.attribute_name})
        canonical_keys = sorted({item.canonical_key for item in records if item.canonical_key})
        entity_refs = [{"entity_id": item.entity_ref.get("entity_id")} for item in records if item.entity_ref.get("entity_id")]
        confidence_values = [item.confidence for item in records]
        relationship_records = [item for item in records if item.evidence_type == "relationship_observation"]
        average_confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.0
        return EvidenceSet(
            records=records,
            entity_refs=entity_refs,
            attribute_names=attribute_names,
            canonical_keys=canonical_keys,
            coverage_summary={
                "observed_record_count": len(records),
                "observed_attribute_count": len(attribute_names),
                "observed_canonical_key_count": len(canonical_keys),
                "relationship_observation_count": len(relationship_records),
                "relationship_truth_eligible_count": len([item for item in relationship_records if item.truth_eligible]),
            },
            confidence_summary={
                "average_confidence": round(average_confidence, 4),
                "minimum_confidence": min(confidence_values) if confidence_values else 0.0,
                "maximum_confidence": max(confidence_values) if confidence_values else 0.0,
            },
        )

    def semantic_coverage(
        self,
        *,
        plan: ContractObservationPlan,
        candidate_set: CandidateEntitySet,
        observation_plan: ObservationPlan,
        observations: list[AttributeObservation],
    ) -> SemanticCoverage:
        observed_fields = sorted({
            item.attribute_name
            for item in observations
            if item.observation_state == "observed" and item.confidence >= plan.minimum_confidence
        })
        missing_fields = [
            item.attribute_name
            for item in observation_plan.requirements
            if item.required and item.evidence_required and not item.observed
        ]
        unsupported_fields = [item.attribute_name for item in observation_plan.requirements if item.gap_reason == "OBSERVER_CAPABILITY_MISSING"]
        unsupported_fields.extend(item.attribute_name for item in observation_plan.requirements if item.gap_reason in {"NO_MATCHING_CAPABILITY", "CAPABILITY_REJECTED"})
        ambiguous_fields = [item.attribute_name for item in observation_plan.requirements if item.gap_reason == "ENTITY_AMBIGUOUS"]
        reason_codes = sorted({str(item.gap_reason) for item in observation_plan.requirements if item.gap_reason})
        required_fields = [
            item.attribute_name
            for item in observation_plan.requirements
            if item.required and item.evidence_required
        ]
        ratio = 1.0 if not required_fields else len(set(observed_fields).intersection(required_fields)) / max(1, len(required_fields))
        status = "not_applicable" if not required_fields else "complete" if not missing_fields else "partial"
        return SemanticCoverage(
            status=status,
            coverage_ratio=ratio,
            observed_fields=observed_fields,
            missing_fields=list(dict.fromkeys(missing_fields)),
            unsupported_fields=list(dict.fromkeys(unsupported_fields)),
            ambiguous_fields=list(dict.fromkeys(ambiguous_fields)),
            candidate_entity_count=len(candidate_set.candidates),
            selected_entity_count=len(candidate_set.selected_entity_ids),
            reason_codes=reason_codes,
            coverage_by_domain=self._coverage_by_domain(observation_plan=observation_plan, observations=observations),
            semantic_gaps=observation_plan.semantic_gaps,
        )

    def semantic_coverage_report(
        self,
        *,
        plan: ContractObservationPlan,
        candidate_set: CandidateEntitySet,
        observation_plan: ObservationPlan,
        observations: list[AttributeObservation],
        coverage: SemanticCoverage,
        evidence_set: EvidenceSet,
        declared_contract: dict[str, Any],
    ) -> SemanticCoverageReport:
        expected_count = len([item for item in observation_plan.requirements if item.required and item.evidence_required])
        selected_count = len(candidate_set.selected_entity_ids)
        observed_count = len([
            item for item in observation_plan.requirements if item.required and item.evidence_required and item.observed
        ])
        matched_goals = len({
            item.goal_id
            for item in observation_plan.capability_matches
            if item.match_status == "MATCHED" and item.capability_id and not item.missing_preconditions
        })
        evidence_attributes = set(evidence_set.canonical_keys or evidence_set.attribute_names)
        missing_capabilities = [
            item.attribute_name
            for item in observation_plan.requirements
            if item.gap_reason in {"NO_MATCHING_CAPABILITY", "CAPABILITY_REJECTED"}
        ]
        confidence_values = [item.confidence for item in observations if item.observation_state == "observed"]
        semantic_confidence = min(confidence_values) if confidence_values else 0.0
        return SemanticCoverageReport(
            artifact_id=str(declared_contract.get("artifact_id") or "") or None,
            contract_id=plan.contract_id,
            artifact_logical_path=plan.artifact_logical_path,
            artifact_kind=plan.artifact_kind,
            task_run_id=plan.task_run_id,
            unbound_reason=plan.unbound_reason,
            structural_coverage=1.0 if plan.expected_attributes else 0.0,
            entity_coverage=1.0 if selected_count else 0.0,
            attribute_coverage=observed_count / max(1, expected_count) if expected_count else 0.0,
            capability_coverage=matched_goals / max(1, len(observation_plan.observation_goals)) if observation_plan.observation_goals else 0.0,
            evidence_coverage=len(evidence_attributes) / max(1, expected_count) if expected_count else 0.0,
            semantic_confidence=round(semantic_confidence, 4),
            missing_attributes=list(coverage.missing_fields),
            missing_capabilities=list(dict.fromkeys(missing_capabilities)),
            blocking_reasons=list(coverage.reason_codes),
            is_semantically_complete=coverage.status == "complete" and not coverage.semantic_gaps,
        )

    def knowledge_records(self, *, evidence_set: EvidenceSet) -> list[KnowledgeRecord]:
        records: list[KnowledgeRecord] = []
        for evidence in evidence_set.records:
            if not evidence.evidence_id:
                continue
            state = "OBSERVED"
            if evidence.contradictions:
                state = "CONFLICTED"
            elif evidence.confidence >= 0.95:
                state = "VERIFIED"
            elif evidence.confidence <= 0.0:
                state = "INSUFFICIENT_EVIDENCE"
            capability_ids = [evidence.capability_id] if evidence.capability_id else []
            observer_ids = [evidence.observer_id] if evidence.observer_id else []
            acquisition = str(evidence.acquisition_method or "").casefold()
            fact_kind = "OBSERVED_FACT"
            source_kind = "observed"
            derivation_rule: str | None = None
            if evidence.evidence_type == "relationship_observation":
                fact_kind = "RELATIONSHIP_DERIVED_FACT"
                source_kind = "candidate"
                derivation_rule = "relationship_observation_candidate"
            elif "derive" in acquisition or "calculate" in acquisition or "infer" in acquisition:
                fact_kind = "DERIVED_FACT"
                source_kind = "derived"
                derivation_rule = str(evidence.acquisition_method or "derived")
            provenance_refs = [
                str(ref)
                for ref in (evidence.evidence_id, evidence.provenance_trace_id, evidence.raw_ref)
                if ref
            ]
            validation_eligibility = bool(
                evidence.evidence_id
                and state not in {"CONFLICTED", "INSUFFICIENT_EVIDENCE"}
                and fact_kind != "RELATIONSHIP_DERIVED_FACT"
            )
            records.append(
                KnowledgeRecord(
                    entity_ref=dict(evidence.entity_ref),
                    attribute_name=evidence.attribute_name,
                    canonical_key=evidence.canonical_key or evidence.attribute_name,
                    value=evidence.normalized_value,
                    state=state,  # type: ignore[arg-type]
                    fact_kind=fact_kind,
                    source_kind=source_kind,
                    evidence_ids=[evidence.evidence_id],
                    provenance_refs=provenance_refs,
                    capability_ids=capability_ids,
                    observer_ids=observer_ids,
                    derivation_rule=derivation_rule,
                    validation_eligibility=validation_eligibility,
                    truth_eligibility=bool(evidence.truth_eligible),
                    confidence=evidence.confidence,
                    provenance={
                        **dict(evidence.provenance or {}),
                        "evidence_id": evidence.evidence_id,
                        "acquisition_method": evidence.acquisition_method,
                        "source": evidence.source,
                    },
                    limitations=list(evidence.limitations),
                    history=[
                        {
                            "event": "knowledge_compiled_from_evidence",
                            "evidence_id": evidence.evidence_id,
                            "confidence": evidence.confidence,
                        }
                    ],
                )
            )
        return records

    def semantic_assertions(
        self,
        *,
        plan: ContractObservationPlan,
        observation_plan: ObservationPlan,
        knowledge_records: list[KnowledgeRecord],
        evidence_set: EvidenceSet,
    ) -> list[SemanticAssertion]:
        knowledge_by_key: dict[str, list[KnowledgeRecord]] = {}
        for item in knowledge_records:
            key = item.canonical_key or item.attribute_name or ""
            if key:
                knowledge_by_key.setdefault(key, []).append(item)
        records_by_id = {item.evidence_id: item for item in evidence_set.records}
        assertions: list[SemanticAssertion] = []
        for requirement in observation_plan.requirements:
            key = requirement.canonical_key or requirement.attribute_name
            related_knowledge = knowledge_by_key.get(key, [])
            evidence_ids = [evidence_id for item in related_knowledge for evidence_id in item.evidence_ids]
            provenance_refs = [
                ref
                for item in related_knowledge
                for ref in item.provenance_refs
                if ref
            ]
            capability_ids = sorted({capability_id for item in related_knowledge for capability_id in item.capability_ids if capability_id})
            confidence = max([item.confidence for item in related_knowledge], default=0.0)
            contradictions = [
                contradiction
                for evidence_id in evidence_ids
                for contradiction in records_by_id.get(evidence_id, EvidenceRecord()).contradictions
            ]
            if contradictions:
                state = "CONFLICTED"
                blocking_reasons = ["EVIDENCE_CONFLICT"]
            elif related_knowledge and confidence >= max(plan.minimum_confidence, requirement.confidence):
                state = "OBSERVED"
                blocking_reasons = []
            elif requirement.required and requirement.evidence_required:
                state = "INSUFFICIENT_EVIDENCE"
                blocking_reasons = [requirement.gap_reason or "EVIDENCE_MISSING"]
            else:
                state = "UNKNOWN"
                blocking_reasons = []
            source_kinds = {item.source_kind for item in related_knowledge if item.source_kind}
            if not related_knowledge:
                fact_kind = "CANDIDATE_FACT"
                source_kind = "candidate"
                derivation_rule = None
            elif source_kinds and source_kinds.issubset({"derived"}):
                fact_kind = "DERIVED_FACT"
                source_kind = "derived"
                derivation_rule = "contract_assertion_from_derived_knowledge"
            else:
                fact_kind = "OBSERVED_FACT"
                source_kind = "observed"
                derivation_rule = "contract_assertion_from_observed_knowledge"
            validation_eligibility = bool(related_knowledge and not blocking_reasons)
            assertions.append(
                SemanticAssertion(
                    assertion_kind="observation" if related_knowledge else "hypothesis",
                    state=state,  # type: ignore[arg-type]
                    subject_ref={
                        "contract_id": plan.contract_id,
                        "artifact_id": plan.artifact_id,
                        "artifact_logical_path": plan.artifact_logical_path,
                    },
                    predicate="attribute_satisfies_contract" if related_knowledge else "attribute_requires_observation",
                    object_value=related_knowledge[0].value if related_knowledge else None,
                    fact_kind=fact_kind,
                    source_kind=source_kind,
                    attribute_name=requirement.attribute_name,
                    canonical_key=key,
                    evidence_ids=evidence_ids,
                    knowledge_ids=[item.knowledge_id for item in related_knowledge],
                    provenance_refs=list(dict.fromkeys(provenance_refs)),
                    capability_ids=capability_ids,
                    derivation_rule=derivation_rule,
                    validation_eligibility=validation_eligibility,
                    confidence=confidence,
                    truth_eligible=bool(related_knowledge and not blocking_reasons and confidence >= plan.minimum_confidence),
                    blocking_reasons=list(dict.fromkeys(blocking_reasons)),
                    limitations=[limitation for item in related_knowledge for limitation in item.limitations],
                    provenance={
                        "contract_observation_plan_id": plan.plan_id,
                        "observation_goal_id": requirement.observation_goal_id,
                        "capability_decision_id": requirement.capability_decision_id,
                    },
                )
            )
        return assertions

    def semantic_self_review(
        self,
        *,
        plan: ContractObservationPlan,
        observation_plan: ObservationPlan,
        evidence_set: EvidenceSet,
        knowledge_records: list[KnowledgeRecord],
        assertions: list[SemanticAssertion],
        coverage_report: SemanticCoverageReport,
    ) -> SemanticSelfReview:
        assertions_by_key = {item.canonical_key or item.attribute_name or "": item for item in assertions}
        questions: list[SemanticQualityQuestion] = []
        for requirement in observation_plan.requirements:
            key = requirement.canonical_key or requirement.attribute_name
            assertion = assertions_by_key.get(key)
            evidence_ids = assertion.evidence_ids if assertion else []
            assertion_ids = [assertion.assertion_id] if assertion else []
            required = requirement.required and requirement.evidence_required
            questions.append(
                SemanticQualityQuestion(
                    code="EVIDENCE_PRESENT",
                    dimension="evidence",
                    question="Does the required attribute have supporting evidence?",
                    status="pass" if evidence_ids else "fail" if required else "not_applicable",
                    attribute_name=requirement.attribute_name,
                    canonical_key=key,
                    evidence_ids=evidence_ids,
                    assertion_ids=assertion_ids,
                    reason_code=None if evidence_ids else requirement.gap_reason or "EVIDENCE_MISSING",
                    explanation="Evidence exists for the assertion." if evidence_ids else "No evidence record supports this attribute.",
                    recommendation=None if evidence_ids else "Execute or register a capability that can produce evidence for this attribute.",
                )
            )
            questions.append(
                SemanticQualityQuestion(
                    code="TRACEABILITY_PRESENT",
                    dimension="traceability",
                    question="Can the assertion be traced to evidence and provenance?",
                    status="pass" if evidence_ids and assertion and assertion.knowledge_ids else "fail" if required else "not_applicable",
                    attribute_name=requirement.attribute_name,
                    canonical_key=key,
                    evidence_ids=evidence_ids,
                    assertion_ids=assertion_ids,
                    reason_code=None if evidence_ids else "TRACEABILITY_MISSING",
                    explanation="Assertion is linked to knowledge and evidence." if evidence_ids else "Assertion has no evidence-backed provenance.",
                )
            )
            questions.append(
                SemanticQualityQuestion(
                    code="CONFIDENCE_SUFFICIENT",
                    dimension="confidence",
                    question="Is confidence sufficient for the declared contract?",
                    status="pass" if assertion and assertion.truth_eligible else "fail" if required else "not_applicable",
                    attribute_name=requirement.attribute_name,
                    canonical_key=key,
                    evidence_ids=evidence_ids,
                    assertion_ids=assertion_ids,
                    reason_code=None if assertion and assertion.truth_eligible else "CONFIDENCE_OR_EVIDENCE_INSUFFICIENT",
                    explanation="Assertion can be considered by Validation." if assertion and assertion.truth_eligible else "Assertion cannot be promoted to truth yet.",
                )
            )
            questions.append(
                SemanticQualityQuestion(
                    code="HYPOTHESIS_NOT_PROMOTED_AS_FACT",
                    dimension="truth",
                    question="Is unsupported hypothesis prevented from becoming truth?",
                    status="pass" if not assertion or assertion.evidence_ids or not assertion.truth_eligible else "fail",
                    attribute_name=requirement.attribute_name,
                    canonical_key=key,
                    evidence_ids=evidence_ids,
                    assertion_ids=assertion_ids,
                    reason_code=None if not assertion or assertion.evidence_ids or not assertion.truth_eligible else "UNSUPPORTED_ASSERTION_PROMOTED",
                    explanation="Unsupported attributes remain non-truth-eligible.",
                )
            )
        relationship_records = [item for item in evidence_set.records if item.evidence_type == "relationship_observation"]
        if plan.expected_relationships or relationship_records:
            evidence_ids = [item.evidence_id for item in relationship_records]
            provenance_ids = [str(item.provenance_trace_id) for item in relationship_records if item.provenance_trace_id]
            conflicts = [conflict for item in relationship_records for conflict in item.conflicts if isinstance(conflict, dict)]
            questions.append(
                SemanticQualityQuestion(
                    code="RELATIONSHIP_EVIDENCE_PRESENT",
                    dimension="relationship_cognition",
                    question="Does the relationship candidate have supporting EvidenceRecord objects?",
                    status="pass" if evidence_ids else "fail",
                    evidence_ids=evidence_ids,
                    assertion_ids=[],
                    reason_code=None if evidence_ids else "RELATIONSHIP_EVIDENCE_INSUFFICIENT",
                    explanation="Relationship evidence records exist." if evidence_ids else "No relationship evidence record supports the candidate.",
                )
            )
            questions.append(
                SemanticQualityQuestion(
                    code="RELATIONSHIP_PROVENANCE_PRESENT",
                    dimension="relationship_cognition",
                    question="Can the relationship candidate be traced to producer, inputs, signals and policy checks?",
                    status="pass" if provenance_ids else "fail",
                    evidence_ids=evidence_ids,
                    assertion_ids=[],
                    reason_code=None if provenance_ids else "RELATIONSHIP_PROVENANCE_MISSING",
                    explanation="Relationship evidence includes provenance trace references." if provenance_ids else "Relationship evidence is missing provenance trace references.",
                )
            )
            questions.append(
                SemanticQualityQuestion(
                    code="RELATIONSHIP_CONFLICT_PRESENT",
                    dimension="relationship_cognition",
                    question="Are relationship conflicts absent or resolved before future validation readiness?",
                    status="fail" if conflicts else "pass",
                    evidence_ids=evidence_ids,
                    assertion_ids=[],
                    reason_code="RELATIONSHIP_CONFLICT_PRESENT" if conflicts else None,
                    explanation="Unresolved relationship conflicts are present." if conflicts else "No relationship conflicts are attached to the candidate evidence.",
                )
            )
            questions.append(
                SemanticQualityQuestion(
                    code="RELATIONSHIP_FINAL_VALIDATION_REQUIRED",
                    dimension="relationship_cognition",
                    question="Are relationship candidates kept out of final truth until validated?",
                    status="fail",
                    evidence_ids=evidence_ids,
                    assertion_ids=[],
                    reason_code="RELATIONSHIP_VALIDATION_REQUIRED" if evidence_ids else "RELATIONSHIP_EVIDENCE_INSUFFICIENT",
                    explanation="Relationship candidates are evidence-backed hypotheses, not final validated relationships.",
                    recommendation="Run a later relationship validation layer before promoting relationship candidates to final claims.",
                )
            )
            questions.append(
                SemanticQualityQuestion(
                    code="RELATIONSHIP_NOT_TRUTH_ELIGIBLE",
                    dimension="truth",
                    question="Are relationship candidates prevented from becoming Speaker Truth?",
                    status="pass",
                    evidence_ids=evidence_ids,
                    assertion_ids=[],
                    reason_code="RELATIONSHIP_TRUTH_NOT_ELIGIBLE",
                    explanation="Relationship observations remain truth_eligible=false.",
                )
            )
        failures = [item for item in questions if item.status == "fail"]
        reason_codes = sorted({item.reason_code for item in failures if item.reason_code})
        truth_ready = coverage_report.is_semantically_complete and not failures
        return SemanticSelfReview(
            artifact_id=plan.artifact_id,
            contract_id=plan.contract_id,
            artifact_logical_path=plan.artifact_logical_path,
            task_run_id=plan.task_run_id,
            questions=questions,
            assertion_count=len(assertions),
            evidence_count=len(evidence_set.records),
            knowledge_count=len(knowledge_records),
            findings=[
                {
                    "code": item.code,
                    "dimension": item.dimension,
                    "attribute_name": item.attribute_name,
                    "canonical_key": item.canonical_key,
                    "reason_code": item.reason_code,
                    "explanation": item.explanation,
                }
                for item in failures
            ],
            truth_readiness="complete" if truth_ready else "blocked" if failures else "partial",
            can_promote_to_validation=truth_ready,
            can_speaker_claim=truth_ready,
            reason_codes=reason_codes,
        )

    def semantic_coverage_2(
        self,
        *,
        coverage_report: SemanticCoverageReport,
        knowledge_records: list[KnowledgeRecord],
        assertions: list[SemanticAssertion],
        self_review: SemanticSelfReview,
    ) -> SemanticCoverage2:
        expected_count = max(1, len({item.canonical_key for item in assertions if item.canonical_key}))
        knowledge_keys = {item.canonical_key for item in knowledge_records if item.canonical_key}
        truth_ready_keys = {item.canonical_key for item in assertions if item.canonical_key and item.truth_eligible}
        knowledge_coverage = len(knowledge_keys) / expected_count
        truth_coverage = len(truth_ready_keys) / expected_count
        dimensions = {
            "structural": coverage_report.structural_coverage,
            "entity": coverage_report.entity_coverage,
            "attribute": coverage_report.attribute_coverage,
            "capability": coverage_report.capability_coverage,
            "evidence": coverage_report.evidence_coverage,
            "knowledge": knowledge_coverage,
            "truth": truth_coverage,
        }
        semantic_coverage = sum(dimensions.values()) / len(dimensions) if dimensions else 0.0
        return SemanticCoverage2(
            structural_coverage=round(coverage_report.structural_coverage, 4),
            entity_coverage=round(coverage_report.entity_coverage, 4),
            attribute_coverage=round(coverage_report.attribute_coverage, 4),
            capability_coverage=round(coverage_report.capability_coverage, 4),
            evidence_coverage=round(coverage_report.evidence_coverage, 4),
            knowledge_coverage=round(knowledge_coverage, 4),
            semantic_coverage=round(semantic_coverage, 4),
            truth_coverage=round(truth_coverage, 4),
            dimension_statuses={name: self._coverage_status(value) for name, value in dimensions.items()},
            blocking_reasons=list(dict.fromkeys([*coverage_report.blocking_reasons, *self_review.reason_codes])),
            warnings=[],
            is_truth_ready=self_review.can_speaker_claim,
        )

    def _fact_kind_counts(
        self,
        *,
        knowledge_records: list[KnowledgeRecord],
        assertions: list[SemanticAssertion],
    ) -> dict[str, int]:
        observed = 0
        derived = 0
        candidate = 0
        for item in [*knowledge_records, *assertions]:
            fact_kind = str(getattr(item, "fact_kind", "") or "").upper()
            source_kind = str(getattr(item, "source_kind", "") or "").casefold()
            if fact_kind == "CANDIDATE_FACT" or source_kind == "candidate":
                candidate += 1
            elif fact_kind in {"DERIVED_FACT", "RELATIONSHIP_DERIVED_FACT"} or source_kind == "derived":
                derived += 1
            elif fact_kind == "OBSERVED_FACT" or source_kind == "observed":
                observed += 1
        return {
            "observed_fact_count": observed,
            "derived_fact_count": derived,
            "candidate_fact_count": candidate,
        }

    def _fact_source_indexes(
        self,
        *,
        observation_plan: ObservationPlan,
        execution_results: list[Any] | None = None,
    ) -> dict[str, Any]:
        requirement_by_attribute = {item.attribute_name: item for item in observation_plan.requirements}
        decision_by_id = {item.decision_id: item for item in observation_plan.capability_decisions}
        capability_ids = {
            str(decision.selected_capability_id)
            for decision in observation_plan.capability_decisions
            if decision.selected_capability_id
        }
        capability_by_id = {capability_id: self.observer_registry.get(capability_id) for capability_id in capability_ids}
        execution_evidence = self._execution_evidence_by_entity_attribute(execution_results or [])
        return {
            "requirement_by_attribute": requirement_by_attribute,
            "decision_by_id": decision_by_id,
            "capability_by_id": capability_by_id,
            "execution_evidence_by_entity_attribute": execution_evidence,
            "policy": {"attribute_projection_checkpoint_interval": 250},
            "metrics": {
                "observation_requirement_count": len(requirement_by_attribute),
                "capability_decision_count": len(decision_by_id),
                "capability_index_entry_count": len(capability_by_id),
                "source_index_entry_count": len(requirement_by_attribute) + len(decision_by_id) + len(execution_evidence),
                "observation_record_count": len(execution_evidence),
            },
        }

    def _attribute_observation_metrics(self, observations: list[AttributeObservation]) -> dict[str, Any]:
        return {
            "attribute_observation_count": len(observations),
            "missing_observation_count": len([item for item in observations if item.observation_state == "missing"]),
            "unsupported_observation_count": len([item for item in observations if item.observation_state == "unsupported"]),
            "failed_observation_count": len([item for item in observations if item.observation_state == "low_confidence"]),
            "observed_null_count": len(
                [
                    item
                    for item in observations
                    if item.observation_state == "observed" and item.observed_value is None
                ]
            ),
            "materialized_bytes_estimate": len(observations) * 180,
        }

    def _evidence_ref_metrics(self, observations: list[AttributeObservation]) -> dict[str, Any]:
        refs = [ref for item in observations for ref in item.evidence_refs if ref]
        return {
            "evidence_ref_count": len(refs),
            "unique_evidence_ref_count": len(set(refs)),
            "duplicate_evidence_ref_avoided_count": max(0, len(refs) - len(set(refs))),
        }

    def _evidence_set_metrics(self, evidence_set: EvidenceSet) -> dict[str, Any]:
        return {
            "evidence_set_count": 1,
            "evidence_record_count": len(evidence_set.records),
            "evidence_record_referenced_count": len({item.raw_ref for item in evidence_set.records if item.raw_ref}),
            "evidence_record_copied_count": len(evidence_set.records),
            "materialized_bytes_estimate": len(evidence_set.records) * 260,
        }

    def _provenance_ref_count(self, evidence_set: EvidenceSet) -> int:
        refs = set()
        for item in evidence_set.records:
            if item.evidence_id:
                refs.add(item.evidence_id)
            if item.raw_ref:
                refs.add(str(item.raw_ref))
            if item.provenance_trace_id:
                refs.add(item.provenance_trace_id)
            for value in (item.provenance or {}).values():
                if isinstance(value, str) and value:
                    refs.add(value)
        return len(refs)

    def _source_binding_bound_reason(self, *, metrics: dict[str, Any], policy: dict[str, Any]) -> str | None:
        max_observations = policy.get("max_attribute_observations")
        if max_observations is not None and int(metrics.get("attribute_observation_count") or 0) > int(max_observations):
            return "PERCEPTION_FACT_SOURCE_BINDING_BOUND_EXCEEDED"
        max_evidence_records = policy.get("max_evidence_records")
        if max_evidence_records is not None and int(metrics.get("evidence_record_count") or 0) > int(max_evidence_records):
            return "PERCEPTION_FACT_SOURCE_BINDING_BOUND_EXCEEDED"
        return None

    def _fact_projection_bound_reason(
        self,
        *,
        metrics: dict[str, Any],
        policy: dict[str, Any],
        fact_projection_started: float,
    ) -> str | None:
        projected = int(metrics.get("projected_fact_count") or 0)
        max_projected = policy.get("max_projected_facts")
        if max_projected is not None and projected > int(max_projected):
            return "PERCEPTION_FACT_PROJECTION_BOUND_EXCEEDED"
        entity_count = max(1, int(metrics.get("projected_entity_count") or metrics.get("input_entity_count") or 1))
        facts_per_entity = projected / entity_count
        max_per_entity = policy.get("max_facts_per_entity")
        if max_per_entity is not None and facts_per_entity > float(max_per_entity):
            return "PERCEPTION_FACT_PROJECTION_BOUND_EXCEEDED"
        max_derivation_ms = policy.get("max_fact_derivation_ms")
        elapsed_ms = (time.monotonic() - fact_projection_started) * 1000
        if max_derivation_ms is not None and elapsed_ms > float(max_derivation_ms):
            return "PERCEPTION_FACT_PROJECTION_COMPLEXITY_BUDGET_EXCEEDED"
        return None

    def _apply_perception_block_reason(
        self,
        *,
        semantic_self_review: SemanticSelfReview,
        semantic_coverage_2: SemanticCoverage2,
        reason_code: str,
    ) -> tuple[SemanticSelfReview, SemanticCoverage2]:
        return (
            semantic_self_review.model_copy(
                update={
                    "truth_readiness": "blocked",
                    "can_promote_to_validation": False,
                    "can_speaker_claim": False,
                    "reason_codes": list(dict.fromkeys([*semantic_self_review.reason_codes, reason_code])),
                }
            ),
            semantic_coverage_2.model_copy(
                update={
                    "blocking_reasons": list(dict.fromkeys([*semantic_coverage_2.blocking_reasons, reason_code])),
                    "is_truth_ready": False,
                }
            ),
        )

    def execute_observation_tasks(
        self,
        *,
        observation_plan: ObservationPlan,
        selected_entities: list[dict[str, Any]],
        max_executions: int | None = None,
    ) -> list[Any]:
        entities_by_id = {str(entity.get("entity_id") or ""): entity for entity in selected_entities}
        results: list[Any] = []
        cache: dict[tuple[str, str], Any] = {}
        strategies_by_id = {item.strategy_id: item for item in observation_plan.observation_strategies}
        for task in observation_plan.observation_tasks:
            if task.status != "READY_FOR_OBSERVER" or not task.capability_id:
                continue
            strategy = strategies_by_id.get(str(task.strategy_id or ""))
            if strategy is None or strategy.strategy_kind != "execute_observer":
                continue
            capability = self.observer_registry.get(task.capability_id)
            target_ids = [str(item) for item in task.entity_ref.get("entity_ids") or [] if str(item)]
            for entity_id in target_ids:
                entity = entities_by_id.get(entity_id)
                if entity is None:
                    continue
                cache_key = (entity_id, str(task.capability_id))
                if cache_key in cache:
                    continue
                if max_executions is not None and len(results) >= max(0, int(max_executions)):
                    return results
                entity_ref = self._execution_entity_ref(entity=entity, capability_id=str(task.capability_id))
                file_path = self._entity_file_path(entity)
                execution_task = task.model_copy(
                    update={
                        "entity_ref": entity_ref,
                        "inputs": {
                            **dict(task.inputs or {}),
                            "entity_id": entity_id,
                            "file_path": file_path or "",
                            "entity_role": entity_ref.get("entity_role"),
                            "source_root_role": entity_ref.get("source_root_role"),
                            "required_confidence": task.inputs.get("required_confidence", 0.0),
                        },
                        "expected_outputs": sorted(MEDIA_METADATA_EVIDENCE_KEYS)
                        if task.capability_id == "media_metadata_reader"
                        else list(task.expected_outputs),
                    }
                )
                result = self.observation_boundary.execute(task=execution_task, capability=capability)
                cache[cache_key] = result
                results.append(result)
        return results

    def _compile_policy(self, declared_contract: dict[str, Any]) -> dict[str, Any]:
        raw = declared_contract.get("perception_compile_policy") if isinstance(declared_contract.get("perception_compile_policy"), dict) else {}
        compile_only = str(raw.get("mode") or "").casefold() in {"compile_only", "bounded_compile", "projection_only"}
        execute_observers = bool(raw.get("execute_observers", not compile_only))
        execute_relationship_detection = bool(raw.get("execute_relationship_detection", not compile_only))
        max_observer_executions = raw.get("max_observer_executions")
        if max_observer_executions is None and compile_only:
            max_observer_executions = 0
        max_materialized_payload_bytes = raw.get("max_materialized_payload_bytes", raw.get("max_payload_bytes", 2_000_000))
        max_payload_items = raw.get("max_payload_items", 250_000)
        max_projected_facts = raw.get("max_projected_facts")
        max_facts_per_entity = raw.get("max_facts_per_entity")
        max_fact_derivation_ms = raw.get("max_fact_derivation_ms")
        max_attribute_observations = raw.get("max_attribute_observations")
        max_evidence_records = raw.get("max_evidence_records")
        return {
            "mode": str(raw.get("mode") or ("compile_only" if compile_only else "full_compile")),
            "execute_observers": execute_observers,
            "execute_relationship_detection": execute_relationship_detection,
            "max_observer_executions": None if max_observer_executions is None else max(0, int(max_observer_executions)),
            "max_materialized_payload_bytes": max(1, int(max_materialized_payload_bytes)),
            "max_payload_items": max(1, int(max_payload_items)),
            "max_projected_facts": None if max_projected_facts is None else max(1, int(max_projected_facts)),
            "max_facts_per_entity": None if max_facts_per_entity is None else max(0.0, float(max_facts_per_entity)),
            "max_fact_derivation_ms": None if max_fact_derivation_ms is None else max(0.0, float(max_fact_derivation_ms)),
            "max_attribute_observations": None if max_attribute_observations is None else max(1, int(max_attribute_observations)),
            "max_evidence_records": None if max_evidence_records is None else max(1, int(max_evidence_records)),
            "stage_trace_enabled": bool(raw.get("stage_trace_enabled", True)),
            "caller_component": str(raw.get("caller_component") or "contract_driven_perception_service"),
        }

    def _public_compile_policy(self, policy: dict[str, Any]) -> dict[str, Any]:
        return {
            "mode": policy.get("mode"),
            "execute_observers": bool(policy.get("execute_observers")),
            "execute_relationship_detection": bool(policy.get("execute_relationship_detection")),
            "max_observer_executions": policy.get("max_observer_executions"),
            "max_materialized_payload_bytes": policy.get("max_materialized_payload_bytes"),
            "max_payload_items": policy.get("max_payload_items"),
            "max_projected_facts": policy.get("max_projected_facts"),
            "max_facts_per_entity": policy.get("max_facts_per_entity"),
            "max_fact_derivation_ms": policy.get("max_fact_derivation_ms"),
            "max_attribute_observations": policy.get("max_attribute_observations"),
            "max_evidence_records": policy.get("max_evidence_records"),
            "caller_component": policy.get("caller_component"),
        }

    def _append_compile_stage(
        self,
        trace: list[dict[str, Any]],
        stage: str,
        *,
        compile_started: float,
        stage_observer: Callable[[dict[str, Any]], None] | None = None,
        **metrics: Any,
    ) -> None:
        bounded_metrics = self._bounded_metrics(metrics)
        item = {
            "stage": stage,
            "elapsed_ms": round((time.monotonic() - compile_started) * 1000, 3),
            "bounded": True,
            **bounded_metrics,
        }
        trace.append(item)
        if stage_observer is not None:
            try:
                stage_observer(item)
            except Exception:
                return

    def _bounded_metrics(self, metrics: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "input_entity_count",
            "declared_attribute_count",
            "required_attribute_count",
            "relationship_requirement_count",
            "candidate_entity_count",
            "projected_entity_count",
            "semantic_gap_count",
            "relationship_candidate_count",
            "relationship_evidence_count",
            "observation_goal_count",
            "observation_strategy_count",
            "observation_task_count",
            "capability_match_count",
            "observation_execution_result_count",
            "attribute_observation_count",
            "observations_in",
            "relationships_in",
            "evidence_record_count",
            "knowledge_record_count",
            "semantic_assertion_count",
            "candidate_fact_count",
            "observed_fact_count",
            "derived_fact_count",
            "projected_fact_count",
            "deduplicated_fact_count",
            "facts_with_evidence_count",
            "facts_with_provenance_count",
            "truth_eligible_count",
            "fact_provenance_issue_count",
            "fact_projection_elapsed_ms",
            "entity_count",
            "source_entity_processed_count",
            "observation_requirement_count",
            "observation_record_count",
            "attribute_observation_attempt_count",
            "evidence_ref_count",
            "unique_evidence_ref_count",
            "duplicate_evidence_ref_avoided_count",
            "evidence_set_count",
            "evidence_record_referenced_count",
            "evidence_record_copied_count",
            "evidence_record_materialized_count",
            "provenance_ref_count",
            "missing_observation_count",
            "unsupported_observation_count",
            "failed_observation_count",
            "observed_null_count",
            "materialized_bytes_estimate",
            "source_index_entry_count",
            "capability_decision_count",
            "capability_index_entry_count",
            "payload_item_count",
            "estimated_payload_bytes",
            "materialized_payload_bytes",
            "payload_ref_count",
            "bound_status",
            "reason_code",
        }
        bounded: dict[str, Any] = {}
        for key, value in metrics.items():
            if key not in allowed:
                continue
            if isinstance(value, (int, float, str, bool)) or value is None:
                bounded[key] = value
        return bounded

    def _graph_entity_count(self, graph: dict[str, Any]) -> int:
        return len([item for item in graph.get("entities") or [] if isinstance(item, dict)])

    def _perception_payload_metrics(
        self,
        *,
        trace: list[dict[str, Any]],
        metrics: dict[str, Any],
        policy: dict[str, Any],
    ) -> dict[str, Any]:
        payload_item_count = sum(
            int(metrics.get(key) or 0)
            for key in (
                "candidate_entity_count",
                "projected_entity_count",
                "relationship_candidate_count",
                "relationship_evidence_count",
                "observation_goal_count",
                "observation_task_count",
                "capability_match_count",
                "observation_execution_result_count",
                "attribute_observation_count",
                "evidence_record_count",
                "knowledge_record_count",
                "semantic_assertion_count",
                "candidate_fact_count",
                "observed_fact_count",
                "derived_fact_count",
                "projected_fact_count",
                "deduplicated_fact_count",
                "facts_with_evidence_count",
                "facts_with_provenance_count",
                "truth_eligible_count",
                "evidence_ref_count",
                "unique_evidence_ref_count",
                "duplicate_evidence_ref_avoided_count",
                "evidence_set_count",
                "evidence_record_referenced_count",
                "evidence_record_copied_count",
                "provenance_ref_count",
                "missing_observation_count",
                "unsupported_observation_count",
                "failed_observation_count",
                "observed_null_count",
            )
        )
        estimated_payload_bytes = (
            int(metrics.get("candidate_entity_count") or 0) * 180
            + int(metrics.get("projected_entity_count") or 0) * 120
            + int(metrics.get("attribute_observation_count") or 0) * 220
            + int(metrics.get("evidence_record_count") or 0) * 260
            + int(metrics.get("relationship_candidate_count") or 0) * 220
            + int(metrics.get("projected_fact_count") or 0) * 120
            + len(trace) * 160
        )
        return {
            **{key: value for key, value in metrics.items() if isinstance(value, (int, float, str, bool))},
            "payload_item_count": payload_item_count,
            "estimated_payload_bytes": estimated_payload_bytes,
            "materialized_payload_bytes": estimated_payload_bytes,
            "payload_ref_count": 0,
            "max_materialized_payload_bytes": policy.get("max_materialized_payload_bytes"),
            "max_payload_items": policy.get("max_payload_items"),
        }

    def _payload_bound_reason(self, *, payload_metrics: dict[str, Any], policy: dict[str, Any]) -> str | None:
        if int(payload_metrics.get("payload_item_count") or 0) > int(policy.get("max_payload_items") or 0):
            return "PERCEPTION_PAYLOAD_BOUND_EXCEEDED"
        if int(payload_metrics.get("materialized_payload_bytes") or 0) > int(policy.get("max_materialized_payload_bytes") or 0):
            return "PERCEPTION_PAYLOAD_BOUND_EXCEEDED"
        return None

    def _mark_observer_execution_deferred(self, observation_plan: ObservationPlan) -> ObservationPlan:
        tasks: list[ObservationTask] = []
        for task in observation_plan.observation_tasks:
            if task.status != "READY_FOR_OBSERVER":
                tasks.append(task)
                continue
            tasks.append(task.model_copy(update={"status": "PLANNED"}))
        requirements: list[AttributeObservationRequirement] = []
        for requirement in observation_plan.requirements:
            if requirement.gap_reason != "ATTRIBUTE_VALUE_NOT_OBSERVED":
                requirements.append(requirement)
                continue
            requirements.append(
                requirement.model_copy(
                    update={
                        "gap_reason": "OBSERVER_EXECUTION_DEFERRED_BY_COMPILE_POLICY",
                        "explanation": "The perception compiler selected a governed observer, but execution is deferred outside the compile boundary.",
                        "recommendation": "Run the selected observation capability in the governed observation boundary before claiming observed metadata.",
                    }
                )
            )
        semantic_gaps = []
        for gap in observation_plan.semantic_gaps:
            if str(gap.get("reason_code") or "") != "ATTRIBUTE_VALUE_NOT_OBSERVED":
                semantic_gaps.append(gap)
                continue
            details = dict(gap.get("details") or {})
            details["reason_chain"] = ["ATTRIBUTE_NOT_OBSERVED", "OBSERVER_EXECUTION_DEFERRED_BY_COMPILE_POLICY"]
            semantic_gaps.append(
                {
                    **gap,
                    "reason_code": "OBSERVER_EXECUTION_DEFERRED_BY_COMPILE_POLICY",
                    "perception_domain": "observer_execution_boundary",
                    "details": details,
                }
            )
        return observation_plan.model_copy(update={"observation_tasks": tasks, "requirements": requirements, "semantic_gaps": semantic_gaps})

    def _apply_execution_evidence_to_plan(
        self,
        *,
        observation_plan: ObservationPlan,
        execution_results: list[Any],
    ) -> ObservationPlan:
        confidence_by_key: dict[str, float] = {}
        capability_ids_by_key: dict[str, list[str]] = {}
        failure_by_key = self._execution_failure_reason_by_key(execution_results)
        for result in execution_results:
            evidence_set = getattr(result, "evidence_set", None)
            for record in getattr(evidence_set, "records", []) or []:
                key = str(record.canonical_key or record.attribute_name or "")
                if not key:
                    continue
                confidence_by_key[key] = max(confidence_by_key.get(key, 0.0), float(record.confidence or 0.0))
                if record.capability_id:
                    capability_ids_by_key.setdefault(key, []).append(str(record.capability_id))
        if not confidence_by_key:
            return observation_plan
        observed_keys = set(confidence_by_key)
        requirements: list[AttributeObservationRequirement] = []
        for requirement in observation_plan.requirements:
            key = requirement.canonical_key or requirement.attribute_name
            if key not in observed_keys:
                if key in failure_by_key and requirement.required:
                    reason = failure_by_key[key]["reason_code"]
                    requirements.append(
                        requirement.model_copy(
                            update={
                                "gap_reason": reason,
                                "explanation": failure_by_key[key]["explanation"],
                                "recommendation": self._recommendation_for_gap_reason(reason),
                            }
                        )
                    )
                    continue
                requirements.append(requirement)
                continue
            requirements.append(
                requirement.model_copy(
                    update={
                        "observed": True,
                        "confidence": confidence_by_key[key],
                        "gap_reason": None,
                        "explanation": "Attribute observed through the ObservationExecutionBoundary.",
                        "recommendation": None,
                        "observer_capability_ids": list(dict.fromkeys([
                            *requirement.observer_capability_ids,
                            *capability_ids_by_key.get(key, []),
                        ])),
                    }
                )
            )
        semantic_gaps: list[dict[str, Any]] = []
        for gap in observation_plan.semantic_gaps:
            key = self._gap_attribute_key(gap)
            if key in observed_keys:
                continue
            if key in failure_by_key and str(gap.get("gap_type") or "").startswith("ATTRIBUTE_NOT_OBSERVED:"):
                reason = failure_by_key[key]["reason_code"]
                details = dict(gap.get("details") or {})
                details.update(
                    {
                        "reason_chain": self._reason_chain(reason),
                        "execution_errors": failure_by_key[key]["errors"],
                        "explanation": failure_by_key[key]["explanation"],
                        "recommendation": self._recommendation_for_gap_reason(reason),
                    }
                )
                semantic_gaps.append(
                    {
                        **gap,
                        "reason_code": reason,
                        "perception_domain": self._domain_for_gap_reason(reason),
                        "details": details,
                    }
                )
                continue
            semantic_gaps.append(gap)
        return observation_plan.model_copy(update={"requirements": requirements, "semantic_gaps": semantic_gaps})

    def _execution_failure_reason_by_key(self, execution_results: list[Any]) -> dict[str, dict[str, Any]]:
        rows: dict[str, dict[str, Any]] = {}
        for result in execution_results:
            evidence_set = getattr(result, "evidence_set", None)
            if getattr(evidence_set, "records", []) or []:
                continue
            keys = [self.observed_entities.canonical_attribute_name(item) for item in getattr(result, "evidence_set", EvidenceSet()).canonical_keys or []]
            if not keys:
                task_outputs = getattr(result, "provenance", {}).get("expected_outputs") if isinstance(getattr(result, "provenance", {}), dict) else None
                keys = [self.observed_entities.canonical_attribute_name(item) for item in task_outputs or []]
            if not keys:
                keys = list(MEDIA_METADATA_EVIDENCE_KEYS) if getattr(result, "capability_id", None) == "media_metadata_reader" else []
            errors = self._execution_error_codes(result)
            reason = self._prioritized_execution_reason(errors)
            for key in keys:
                if key in rows:
                    continue
                rows[key] = {
                    "reason_code": reason,
                    "errors": errors,
                    "explanation": "Observation execution ran or was attempted, but no valid EvidenceRecord was produced for this required attribute.",
                }
        return rows

    def _execution_error_codes(self, result: Any) -> list[str]:
        codes = [str(error.code) for error in getattr(result, "errors", []) or [] if getattr(error, "code", None)]
        payload = getattr(result, "provenance", {}) if isinstance(getattr(result, "provenance", {}), dict) else {}
        observer_payload = payload.get("observer_payload") if isinstance(payload.get("observer_payload"), dict) else {}
        media_summary = observer_payload.get("media_metadata_capability") if isinstance(observer_payload.get("media_metadata_capability"), dict) else {}
        for error in media_summary.get("errors", []) or []:
            if isinstance(error, dict) and error.get("code"):
                codes.append(str(error.get("code")))
        return list(dict.fromkeys(codes or ["OBSERVER_PRODUCED_NO_EVIDENCE"]))

    def _prioritized_execution_reason(self, codes: list[str]) -> str:
        priority = [
            "MEDIA_METADATA_OBSERVER_BINDING_MISSING",
            "MEDIA_CAPABILITY_ENTITY_ROLE_REJECTED",
            "MEDIA_CAPABILITY_ROOT_ROLE_REJECTED",
            "MEDIA_CAPABILITY_FILE_PATH_MISSING",
            "MEDIA_BACKEND_NO_EVIDENCE",
            "MEDIA_BACKEND_UNSUPPORTED_FORMAT",
            "MEDIA_BACKEND_LOW_CONFIDENCE",
            "MUTAGEN_NOT_IMPORTABLE",
            "MEDIA_METADATA_DEPENDENCY_MISSING",
            "FFPROBE_NOT_AVAILABLE",
            "MEDIA_BACKEND_NOT_AVAILABLE",
            "OBSERVER_PRODUCED_NO_EVIDENCE",
        ]
        for code in priority:
            if code in codes:
                return code
        return codes[0] if codes else "OBSERVER_PRODUCED_NO_EVIDENCE"

    def _execution_evidence_by_entity_attribute(self, execution_results: list[Any]) -> dict[tuple[str, str], EvidenceRecord]:
        rows: dict[tuple[str, str], EvidenceRecord] = {}
        for result in execution_results:
            evidence_set = getattr(result, "evidence_set", None)
            for record in getattr(evidence_set, "records", []) or []:
                entity_id = str((record.entity_ref or {}).get("entity_id") or "")
                key = str(record.canonical_key or record.attribute_name or "")
                if not entity_id or not key:
                    continue
                current = rows.get((entity_id, key))
                if current is None or record.confidence > current.confidence:
                    rows[(entity_id, key)] = record
        return rows

    def _media_metadata_capability_summary(self, execution_results: list[Any]) -> dict[str, Any]:
        media_results = [item for item in execution_results if getattr(item, "capability_id", None) == "media_metadata_reader"]
        if not media_results:
            return {
                "status": "configured_but_deferred",
                "capability_id": "media_metadata_reader",
                "configured": True,
                "available": True,
                "execution_status": "deferred",
                "files_planned": 0,
                "files_attempted": 0,
                "files_succeeded": 0,
                "files_failed": 0,
                "primary_backend": "mutagen",
                "selected_backend": None,
                "available_backends": [],
                "blocked_backends": [],
                "globally_blocked_backends": [],
                "partially_blocked_backends": [],
                "missing_dependency": [],
                "attempted_backends": [],
                "successful_backends": [],
                "fallback_backends_used": [],
                "backend_error_counts": {},
                "evidence_records_created": 0,
                "attributes_observed": [],
                "attributes_missing": list(MEDIA_METADATA_EVIDENCE_KEYS),
                "limitations": ["media_metadata_observer_execution_deferred"],
                "errors": [],
            }
        summaries: list[dict[str, Any]] = []
        records: list[EvidenceRecord] = []
        errors: list[dict[str, Any]] = []
        limitations: list[str] = []
        for result in media_results:
            payload = getattr(result, "provenance", {}) or {}
            observer_payload = payload.get("observer_payload") if isinstance(payload.get("observer_payload"), dict) else {}
            summary = observer_payload.get("media_metadata_capability") if isinstance(observer_payload.get("media_metadata_capability"), dict) else {}
            if summary:
                summaries.append(summary)
            evidence_set = getattr(result, "evidence_set", None)
            records.extend(getattr(evidence_set, "records", []) or [])
            for error in getattr(result, "errors", []) or []:
                errors.append(error.model_dump(mode="json") if hasattr(error, "model_dump") else dict(error))
            limitations.extend(str(item) for item in getattr(result, "limitations", []) or [] if item)
        observed = sorted({str(record.canonical_key or record.attribute_name) for record in records if record.canonical_key or record.attribute_name})
        selected_backend = next((str(summary.get("selected_backend")) for summary in summaries if summary.get("selected_backend")), None)
        primary_backend = next((str(summary.get("primary_backend")) for summary in summaries if summary.get("primary_backend")), "mutagen")
        attempted_backends = sorted({
            str(item)
            for summary in summaries
            for item in summary.get("attempted_backends", []) or []
            if item
        })
        successful_backends = sorted({
            str(item)
            for summary in summaries
            for item in summary.get("successful_backends", []) or []
            if item
        })
        fallback_backends_used = sorted({
            str(item)
            for summary in summaries
            for item in summary.get("fallback_backends_used", []) or []
            if item
        })
        available_backends = sorted({
            *[
                str(item)
                for summary in summaries
                for item in summary.get("available_backends", []) or []
                if item
            ],
            *[str(record.backend_id) for record in records if record.backend_id],
        })
        backend_attempt_counts: dict[str, int] = {}
        backend_success_counts: dict[str, int] = {}
        backend_block_counts: dict[str, int] = {}
        backend_error_counts: dict[str, int] = {}
        for summary in summaries:
            for backend in summary.get("attempted_backends", []) or []:
                key = str(backend)
                backend_attempt_counts[key] = backend_attempt_counts.get(key, 0) + 1
            for backend in summary.get("successful_backends", []) or []:
                key = str(backend)
                backend_success_counts[key] = backend_success_counts.get(key, 0) + 1
            for backend in summary.get("blocked_backends", []) or []:
                key = str(backend)
                backend_block_counts[key] = backend_block_counts.get(key, 0) + 1
            for code, count in dict(summary.get("backend_error_counts") or {}).items():
                key = str(code)
                backend_error_counts[key] = backend_error_counts.get(key, 0) + int(count or 0)
        blocked_backends = sorted(backend_block_counts)
        globally_blocked_backends = sorted(
            backend
            for backend, count in backend_attempt_counts.items()
            if count > 0 and backend_success_counts.get(backend, 0) == 0 and backend_block_counts.get(backend, 0) >= count
        )
        partially_blocked_backends = sorted(
            backend
            for backend, count in backend_block_counts.items()
            if count > 0 and backend_success_counts.get(backend, 0) > 0
        )
        missing_dependency = sorted({
            str(item)
            for summary in summaries
            for item in summary.get("missing_dependency", []) or []
            if item
        })
        limitations.extend(
            str(item)
            for summary in summaries
            for item in summary.get("limitations", []) or []
            if item
        )
        for summary in summaries:
            for error in summary.get("errors", []) or []:
                if isinstance(error, dict):
                    errors.append(error)
                    code = str(error.get("code") or "")
                    if code:
                        limitations.append(code)
        dependency_error_tokens = ("NOT_AVAILABLE", "NOT_IMPORTABLE", "DEPENDENCY")
        non_dependency_errors = [
            item
            for item in errors
            if isinstance(item, dict)
            and not any(token in str(item.get("code") or "") for token in dependency_error_tokens)
        ]
        files_attempted = len({
            str((getattr(result, "provenance", {}) or {}).get("entity_id") or (getattr(result, "provenance", {}) or {}).get("file_path") or getattr(result, "raw_ref", "") or getattr(result, "observation_task_id", ""))
            for result in media_results
        })
        files_succeeded = len({
            str((record.entity_ref or {}).get("entity_id") or record.raw_ref or "")
            for record in records
            if (record.entity_ref or {}).get("entity_id") or record.raw_ref
        })
        if records:
            status = "available" if set(MEDIA_METADATA_CANONICAL_KEYS).issubset(set(observed)) else "partial"
        elif non_dependency_errors:
            status = "blocked"
        elif missing_dependency:
            status = "missing_dependency"
        elif errors:
            status = "blocked"
        else:
            status = "not_configured"
        return {
            "status": status,
            "capability_id": "media_metadata_reader",
            "configured": True,
            "available": status not in {"missing_dependency", "blocked", "not_configured"},
            "execution_status": "executed" if status in {"available", "partial"} else status,
            "files_planned": files_attempted,
            "files_attempted": files_attempted,
            "files_succeeded": files_succeeded,
            "files_failed": max(0, files_attempted - files_succeeded),
            "primary_backend": primary_backend,
            "selected_backend": selected_backend,
            "available_backends": available_backends,
            "blocked_backends": blocked_backends,
            "globally_blocked_backends": globally_blocked_backends,
            "partially_blocked_backends": partially_blocked_backends,
            "missing_dependency": missing_dependency,
            "attempted_backends": attempted_backends,
            "successful_backends": successful_backends,
            "fallback_backends_used": fallback_backends_used,
            "backend_error_counts": backend_error_counts,
            "evidence_records_created": len(records),
            "attributes_observed": observed,
            "attributes_missing": [key for key in MEDIA_METADATA_EVIDENCE_KEYS if key not in set(observed)],
            "limitations": sorted(set(limitations)),
            "errors": errors,
        }

    def _relationship_summary(self, detection: dict[str, Any]) -> dict[str, Any]:
        candidates = detection.get("candidates") if isinstance(detection.get("candidates"), list) else []
        observations = detection.get("observations") if isinstance(detection.get("observations"), list) else []
        evidence = detection.get("evidence") if isinstance(detection.get("evidence"), list) else []
        families = sorted({
            str(getattr(item, "relation_family", "") or "")
            for item in candidates
            if str(getattr(item, "relation_family", "") or "")
        })
        confidence_values = [float(getattr(item, "confidence", 0.0) or 0.0) for item in candidates]
        conflict_count = sum(len(getattr(item, "conflicts", []) or []) for item in candidates)
        negative_evidence_count = sum(len(getattr(item, "negative_evidence", []) or []) for item in candidates)
        provenance_traces = detection.get("provenance_traces") if isinstance(detection.get("provenance_traces"), list) else []
        return {
            "status": str(detection.get("status") or "not_available"),
            "capability_id": detection.get("capability_id") or MEDIA_RELATIONSHIP_CAPABILITY_ID,
            "candidate_count": len(candidates),
            "observation_count": len(observations),
            "evidence_count": len(evidence),
            "provenance_trace_count": len(provenance_traces),
            "conflict_count": conflict_count,
            "negative_evidence_count": negative_evidence_count,
            "relation_families": families,
            "confidence_summary": {
                "count": len(confidence_values),
                "max": round(max(confidence_values), 4) if confidence_values else 0.0,
                "average": round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 0.0,
            },
            "truth_eligible": False,
            "validation_ready": False,
            "reason_codes": list(detection.get("reason_codes") or []),
            "limitations": list(detection.get("limitations") or []),
            "source": "media_relationship_candidate_detector",
        }

    def _execution_entity_ref(self, *, entity: dict[str, Any], capability_id: str) -> dict[str, Any]:
        entity_id = str(entity.get("entity_id") or "")
        source_root_role = str(entity.get("source_root_role") or self._attribute_payload(entity, "source_root_role").get("value") or "")
        entity_role = str(entity.get("entity_role") or self._attribute_payload(entity, "entity_role").get("value") or "")
        if capability_id == "media_metadata_reader" and source_root_role in {"library_root", "corpus_root"} and entity_role != "media_asset_candidate":
            execution_role = "media_asset_candidate"
        else:
            execution_role = entity_role
        return {
            "entity_id": entity_id,
            "entity_kind": str(entity.get("entity_kind") or "unknown"),
            "entity_role": execution_role,
            "original_entity_role": entity_role,
            "source_root_role": source_root_role,
            "source_root": str(entity.get("source_root") or self._attribute_payload(entity, "source_root").get("value") or ""),
            "relative_path": str(entity.get("relative_path") or self._attribute_payload(entity, "relative_path").get("value") or ""),
            "path": self._entity_file_path(entity),
            "observation_hypothesis": "media_asset_candidate_for_contract_required_metadata" if execution_role != entity_role else None,
        }

    def _entity_file_path(self, entity: dict[str, Any]) -> str | None:
        from pathlib import Path

        for key in ("file_path", "path", "absolute_path"):
            value = entity.get(key)
            if value:
                path = Path(str(value))
                if path.is_absolute():
                    return str(path)
        root = str(entity.get("source_root") or self._attribute_payload(entity, "source_root").get("value") or "")
        relative = str(entity.get("relative_path") or self._attribute_payload(entity, "relative_path").get("value") or "")
        name = str(entity.get("name") or self._attribute_payload(entity, "name").get("value") or "")
        if relative:
            path = Path(relative)
            return str(path if path.is_absolute() else Path(root) / path) if root else str(path)
        if root and name:
            return str(Path(root) / name)
        return None

    def _gap_attribute_key(self, gap: dict[str, Any]) -> str:
        gap_type = str(gap.get("gap_type") or "")
        if gap_type.startswith("ATTRIBUTE_NOT_OBSERVED:"):
            return self.observed_entities.canonical_attribute_name(gap_type.split(":", 1)[1])
        expected = gap.get("expected")
        if isinstance(expected, str):
            return self.observed_entities.canonical_attribute_name(expected)
        return ""

    def _selected_entities(self, graph: dict[str, Any], candidate_set: CandidateEntitySet) -> list[dict[str, Any]]:
        selected_ids = set(candidate_set.selected_entity_ids)
        return [
            item
            for item in graph.get("entities") or []
            if isinstance(item, dict) and str(item.get("entity_id") or "") in selected_ids
        ]

    def _coverage_status(self, value: float) -> str:
        if value >= 1.0:
            return "complete"
        if value > 0.0:
            return "partial"
        return "blocked"

    def _select_candidates(self, candidates: list[CandidateEntity], *, plan: ContractObservationPlan) -> list[CandidateEntity]:
        candidates = [item for item in candidates if item.status != "rejected"]
        if not candidates:
            return []
        best_relevance = max(item.contract_relevance for item in candidates)
        threshold = max(plan.minimum_confidence, best_relevance)
        return [item for item in candidates if item.contract_relevance >= threshold]

    def _relevance(self, *, covered: list[str], potentially_observable: list[str], expected: list[str]) -> float:
        if not expected:
            return 0.0
        score = len(set(covered)) + (0.25 * len(set(potentially_observable)))
        return max(0.0, min(1.0, score / max(1, len(set(expected)))))

    def _strategy_kinds_for_goal(self, *, already_observed: bool) -> list[ObservationStrategyKind]:
        kinds: list[ObservationStrategyKind] = ["read_existing_attribute"]
        if not already_observed:
            kinds.extend(["calculate", "infer_from_evidence", "query_component", "execute_observer", "combine_evidence"])
        return kinds

    def _capability_kind_for_strategy(self, strategy_kind: ObservationStrategyKind) -> str:
        return {
            "read_existing_attribute": "attribute_reader",
            "calculate": "attribute_calculator",
            "infer_from_evidence": "evidence_inference",
            "query_component": "component_query",
            "execute_observer": "observer_execution",
            "combine_evidence": "evidence_combiner",
        }[strategy_kind]

    def _strategy_prerequisites(self, strategy_kind: ObservationStrategyKind) -> list[str]:
        return {
            "read_existing_attribute": ["attribute_present_in_entity_graph"],
            "calculate": ["source_data_available", "calculation_rule_available"],
            "infer_from_evidence": ["supporting_evidence_available", "inference_rule_available"],
            "query_component": ["component_interface_available"],
            "execute_observer": ["observer_capability_available"],
            "combine_evidence": ["multiple_evidence_sources_available"],
        }[strategy_kind]

    def _strategy_cost(self, strategy_kind: ObservationStrategyKind) -> float:
        return {
            "read_existing_attribute": 0.0,
            "calculate": 0.2,
            "infer_from_evidence": 0.4,
            "query_component": 0.5,
            "execute_observer": 0.7,
            "combine_evidence": 0.6,
        }[strategy_kind]

    def _strategy_latency(self, strategy_kind: ObservationStrategyKind) -> int:
        return {
            "read_existing_attribute": 0,
            "calculate": 10,
            "infer_from_evidence": 20,
            "query_component": 50,
            "execute_observer": 100,
            "combine_evidence": 30,
        }[strategy_kind]

    def _strategy_limitations(self, strategy_kind: ObservationStrategyKind) -> list[str]:
        return {
            "read_existing_attribute": ["Requires the attribute to already be present in the observed entity graph."],
            "calculate": ["Requires a declared deterministic calculation rule and source data."],
            "infer_from_evidence": ["Requires supporting evidence and an explicit inference rule."],
            "query_component": ["Requires a component interface that declares compatible observation capability."],
            "execute_observer": ["Requires an observer binding to be available and governed."],
            "combine_evidence": ["Requires multiple compatible evidence records."],
        }[strategy_kind]

    def _strategy_rationale(self, strategy_kind: ObservationStrategyKind) -> str:
        return {
            "read_existing_attribute": "Use a value that already exists in the observed entity graph.",
            "calculate": "Derive the attribute by deterministic computation from available source data.",
            "infer_from_evidence": "Infer the attribute from structured evidence with confidence tracking.",
            "query_component": "Ask another runtime component that declares a compatible observation capability.",
            "execute_observer": "Run an observer that can acquire the attribute from the target entity.",
            "combine_evidence": "Combine multiple structured evidence sources into one AttributeObservation.",
        }[strategy_kind]

    def _attribute_descriptors(self, declared_contract: dict[str, Any]) -> list[AttributeDescriptor]:
        raw_schema = [item for item in declared_contract.get("expected_schema") or [] if str(item).strip()]
        raw_contracts = declared_contract.get("attribute_contracts")
        contracts_by_raw: dict[str, dict[str, Any]] = {}
        contracts_by_key: dict[str, dict[str, Any]] = {}
        if isinstance(raw_contracts, dict):
            for key, value in raw_contracts.items():
                if isinstance(value, dict):
                    data = dict(value)
                    data.setdefault("raw_label", key)
                    contracts_by_raw[str(key)] = data
                    canonical, _ = self.attribute_keys.canonical_key(data.get("canonical_key") or key)
                    contracts_by_key[canonical] = data
        elif isinstance(raw_contracts, list):
            for value in raw_contracts:
                if isinstance(value, dict):
                    data = dict(value)
                    raw = str(data.get("raw_label") or data.get("display_label") or data.get("canonical_key") or "")
                    if raw:
                        contracts_by_raw[raw] = data
                    canonical, _ = self.attribute_keys.canonical_key(data.get("canonical_key") or raw)
                    contracts_by_key[canonical] = data
        requiredness_by_key = {
            self.attribute_keys.canonical_key(key)[0]: value
            for key, value in dict(declared_contract.get("attribute_requiredness") or {}).items()
        }
        descriptors: list[AttributeDescriptor] = []
        seen: set[str] = set()
        for item in raw_schema:
            raw = str(item)
            canonical, _ = self.attribute_keys.canonical_key(raw)
            data = dict(contracts_by_raw.get(raw) or contracts_by_key.get(canonical) or {})
            if canonical in requiredness_by_key:
                data["requiredness"] = requiredness_by_key[canonical]
            descriptor = self.attribute_keys.descriptor(
                raw,
                explicit=data,
                locale=str(declared_contract.get("locale") or "") or None,
            )
            if descriptor.canonical_key in seen:
                continue
            descriptors.append(descriptor)
            seen.add(descriptor.canonical_key)
        return descriptors

    def _entity_selection_contract(self, declared_contract: dict[str, Any]) -> dict[str, Any]:
        explicit = declared_contract.get("entity_selection_contract") or declared_contract.get("artifact_entity_selection_contract")
        if isinstance(explicit, dict) and explicit:
            return dict(explicit)
        workspace_context = declared_contract.get("workspace_context") if isinstance(declared_contract.get("workspace_context"), dict) else {}
        root_policy = self.observed_entities.policy.get("root_role_policy") if isinstance(self.observed_entities.policy.get("root_role_policy"), dict) else {}
        has_library_roots = bool(workspace_context.get("library_roots"))
        expected_kind = str(declared_contract.get("expected_kind") or "")
        if expected_kind == "tabular_collection" and has_library_roots:
            return {
                "selection_mode": "corpus_inventory",
                "expected_entity_role": "corpus_file",
                "expected_entity_domain": "corpus_member",
                "allowed_root_roles": list(root_policy.get("corpus_preferred_root_roles") or ["library_root", "corpus_root"]),
                "excluded_entity_roles": list(root_policy.get("corpus_excluded_entity_roles") or []),
                "source": "workspace_context_library_roots",
            }
        return {
            "selection_mode": "generic_collection",
            "expected_entity_role": None,
            "expected_entity_domain": None,
            "allowed_root_roles": [],
            "excluded_entity_roles": [],
            "source": "default_contract_selection",
        }

    def _entity_policy_rejections(self, *, entity: dict[str, Any], plan: ContractObservationPlan) -> list[str]:
        reasons: list[str] = []
        source_root_role = str(entity.get("source_root_role") or self._attribute_payload(entity, "source_root_role").get("value") or "")
        entity_role = str(entity.get("entity_role") or self._attribute_payload(entity, "entity_role").get("value") or "")
        if plan.allowed_root_roles and not source_root_role:
            reasons.extend(["ROOT_ROLE_METADATA_MISSING", "ENTITY_SELECTED_FROM_UNCLASSIFIED_ROOT"])
        elif plan.allowed_root_roles and source_root_role not in set(plan.allowed_root_roles):
            reasons.append("ROOT_ROLE_NOT_ALLOWED")
        if plan.excluded_entity_roles and entity_role in set(plan.excluded_entity_roles):
            reasons.append("ENTITY_ROLE_EXCLUDED")
        if plan.expected_entity_role and not entity_role:
            reasons.append("ENTITY_ROLE_METADATA_MISSING")
        elif plan.expected_entity_role and entity_role != plan.expected_entity_role:
            reasons.append("ENTITY_ROLE_MISMATCH")
        if plan.expected_entity_domain:
            hypotheses = entity.get("entity_domain_hypotheses") if isinstance(entity.get("entity_domain_hypotheses"), list) else []
            domains = {str(item.get("domain") or "") for item in hypotheses if isinstance(item, dict)}
            if domains and plan.expected_entity_domain not in domains:
                reasons.append("ENTITY_DOMAIN_MISMATCH")
        return list(dict.fromkeys(reasons))

    def _descriptor_for(self, plan: ContractObservationPlan, attribute: str) -> AttributeDescriptor | None:
        canonical = self.attribute_keys.canonical_key(attribute)[0]
        return next((item for item in plan.attribute_contracts if item.canonical_key == canonical), None)

    def _attribute_blocks_completion(self, descriptor: AttributeDescriptor | None) -> bool:
        if descriptor is None:
            return True
        return bool(
            descriptor.evidence_required
            and descriptor.requiredness == "required"
            and not descriptor.nullable
        )

    def _satisfied_strategy_preconditions(
        self,
        *,
        kind: ObservationStrategyKind,
        goal: ObservationGoal,
        selected_entities: list[dict[str, Any]],
        already_observed: bool,
    ) -> list[str]:
        satisfied: list[str] = []
        if kind == "read_existing_attribute" and already_observed:
            satisfied.append("attribute_present_in_entity_graph")
        if kind == "calculate" and any(self._path_source_available(entity) for entity in selected_entities):
            if goal.attribute_name in {"extension", "basename", "stem", "parent_path", "file_name"}:
                satisfied.extend(["source_data_available", "calculation_rule_available", "source_path_or_name_available"])
        if kind == "infer_from_evidence" and goal.evidence_refs:
            satisfied.append("supporting_evidence_available")
        return list(dict.fromkeys(satisfied))

    def _path_source_available(self, entity: dict[str, Any]) -> bool:
        for key in ("relative_path", "name", "source_root"):
            payload = self._attribute_payload(entity, key)
            if payload and payload.get("value") not in (None, ""):
                return True
        return False

    def _derive_file_path_attribute(self, *, entity: dict[str, Any], attribute: str) -> Any | None:
        if str(entity.get("entity_kind") or "") != "file":
            return None
        relative_path, relative_present = self.observed_entities.value_for_field(entity, "relative_path")
        name, name_present = self.observed_entities.value_for_field(entity, "name")
        raw_path = str(relative_path or name or "")
        if not raw_path:
            return None
        from pathlib import PurePath

        path = PurePath(raw_path)
        if attribute == "extension":
            return path.suffix.lstrip(".").casefold()
        if attribute in {"basename", "file_name"}:
            return path.name if relative_present else str(name)
        if attribute == "stem":
            return path.stem
        if attribute == "parent_path":
            parent = str(path.parent)
            return "" if parent == "." and not relative_present else parent
        return None

    def _semantic_type_for_attribute(self, attribute: str, *, plan: ContractObservationPlan) -> str:
        expected_types = plan.constraints.get("expected_semantic_types") if isinstance(plan.constraints, dict) else None
        if isinstance(expected_types, dict) and expected_types.get(attribute):
            return str(expected_types[attribute])
        return "contract_declared_attribute"

    def _evidence_type_for_attribute(self, attribute: str, *, plan: ContractObservationPlan) -> str:
        evidence_types = plan.constraints.get("required_evidence_types") if isinstance(plan.constraints, dict) else None
        if isinstance(evidence_types, dict) and evidence_types.get(attribute):
            return str(evidence_types[attribute])
        return "structured_attribute_evidence"

    def _score_capability_match(
        self,
        *,
        goal: ObservationGoal,
        strategy: ObservationStrategy,
        capability: ObservationCapability,
    ) -> CapabilityMatch:
        conflicts: list[str] = []
        canonical_attribute = self.observed_entities.canonical_attribute_name(goal.attribute_name)
        attributes_covered = [canonical_attribute] if canonical_attribute in capability.observable_attributes else []
        attributes_missing = [] if attributes_covered else [canonical_attribute]
        required_preconditions = list(dict.fromkeys([*strategy.required_preconditions, *capability.preconditions, *capability.dependencies]))
        satisfied_preconditions = list(dict.fromkeys(strategy.satisfied_preconditions))
        if capability.available and strategy.strategy_kind == "execute_observer":
            satisfied_preconditions.append("observer_capability_available")
        if capability.capability_id == "media_metadata_reader":
            selected_root_roles = set(goal.entity_ref.get("source_root_roles") or [])
            canonical_attribute = self.observed_entities.canonical_attribute_name(goal.attribute_name)
            if canonical_attribute in MEDIA_METADATA_CANONICAL_KEYS:
                satisfied_preconditions.append("media_asset_candidate_hypothesis")
            if selected_root_roles.intersection({"library_root", "corpus_root"}):
                satisfied_preconditions.append("source_root_role_library_or_corpus")
            if goal.entity_ref.get("file_path_available"):
                satisfied_preconditions.extend(["file_path_present", "file_exists", "read_access"])
        if capability.available and strategy.strategy_kind == "query_component":
            satisfied_preconditions.append("component_interface_available")
        satisfied_preconditions = list(dict.fromkeys(satisfied_preconditions))
        missing_preconditions = [item for item in required_preconditions if item not in set(satisfied_preconditions)]
        compatible_kinds = set(capability.compatible_entity_kinds)
        normalized_goal_kinds = {self._normalize(kind) for kind in goal.target_entity_kinds if str(kind).strip()}
        if "*" not in compatible_kinds and normalized_goal_kinds and compatible_kinds.isdisjoint(normalized_goal_kinds):
            conflicts.append("entity_kind_incompatible")
        if strategy.strategy_kind not in capability.supported_strategies:
            conflicts.append("strategy_not_supported")
        if not capability.available:
            conflicts.append("capability_unavailable")
        coverage_score = 0.35 if attributes_covered else 0.0
        compatibility_score = 0.2 if "entity_kind_incompatible" not in conflicts else 0.0
        strategy_score = 0.15 if "strategy_not_supported" not in conflicts else 0.0
        availability_score = 0.1 if capability.available else 0.0
        confidence_score = max(0.0, min(0.1, capability.typical_confidence * 0.1))
        efficiency_score = max(0.0, 0.1 - min(0.1, capability.estimated_cost * 0.05 + capability.latency_ms * 0.0001))
        score = coverage_score + compatibility_score + strategy_score + availability_score + confidence_score + efficiency_score
        if missing_preconditions:
            conflicts.append("precondition_missing")
        if conflicts:
            score = min(score, 0.49)
        match_status = "MATCHED" if not conflicts and attributes_covered else "PARTIAL_MATCH"
        blocking_reason = None
        if "capability_unavailable" in conflicts:
            match_status = "PRECONDITION_FAILED"
            blocking_reason = "CAPABILITY_UNAVAILABLE"
        elif "entity_kind_incompatible" in conflicts:
            match_status = "PRECONDITION_FAILED"
            blocking_reason = "ENTITY_KIND_INCOMPATIBLE"
        elif "strategy_not_supported" in conflicts:
            match_status = "PRECONDITION_FAILED"
            blocking_reason = "STRATEGY_NOT_SUPPORTED"
        elif "precondition_missing" in conflicts:
            match_status = "PRECONDITION_FAILED"
            blocking_reason = "PRECONDITION_FAILED"
        return CapabilityMatch(
            goal_id=goal.goal_id,
            strategy_id=strategy.strategy_id,
            capability_id=capability.capability_id,
            contract_id=goal.contract_id,
            artifact_id=goal.artifact_id,
            artifact_logical_path=goal.artifact_logical_path,
            artifact_kind=goal.artifact_kind,
            task_run_id=goal.task_run_id,
            strategy_ids=[strategy.strategy_id],
            attribute_name=goal.attribute_name,
            canonical_key=canonical_attribute,
            match_status=match_status,
            match_score=round(max(0.0, min(1.0, score)), 4),
            coverage_score=round(coverage_score, 4),
            confidence_score=round(capability.typical_confidence, 4),
            score=round(max(0.0, min(1.0, score)), 4),
            score_reason="contract_coverage_entity_compatibility_strategy_availability_confidence_cost_latency",
            attributes_covered=attributes_covered,
            attributes_missing=attributes_missing,
            required_preconditions=required_preconditions,
            satisfied_preconditions=satisfied_preconditions,
            missing_preconditions=missing_preconditions,
            unsupported_attributes=attributes_missing,
            unsupported_entity_type="entity_kind_incompatible" if "entity_kind_incompatible" in conflicts else None,
            unsupported_evidence_type=None,
            blocking_reason=blocking_reason,
            explanation="Capability match scored from contract coverage, entity compatibility, strategy support, availability, confidence, cost, and latency.",
            conflicts=conflicts,
            prerequisites=required_preconditions,
            available=capability.available and not missing_preconditions,
        )

    def _negative_capability_match(self, *, goal: ObservationGoal, strategy: ObservationStrategy) -> CapabilityMatch:
        canonical_attribute = self.observed_entities.canonical_attribute_name(goal.attribute_name)
        return CapabilityMatch(
            goal_id=goal.goal_id,
            strategy_id=strategy.strategy_id,
            capability_id=None,
            contract_id=goal.contract_id,
            artifact_id=goal.artifact_id,
            artifact_logical_path=goal.artifact_logical_path,
            artifact_kind=goal.artifact_kind,
            task_run_id=goal.task_run_id,
            strategy_ids=[strategy.strategy_id],
            attribute_name=goal.attribute_name,
            canonical_key=canonical_attribute,
            match_status="NO_MATCHING_CAPABILITY",
            match_score=0.0,
            coverage_score=0.0,
            confidence_score=0.0,
            score=0.0,
            score_reason="no_registered_capability_for_goal_strategy_attribute_entity",
            attributes_covered=[],
            attributes_missing=[canonical_attribute],
            required_preconditions=list(strategy.required_preconditions),
            satisfied_preconditions=list(strategy.satisfied_preconditions),
            missing_preconditions=list(strategy.missing_preconditions),
            unsupported_attributes=[canonical_attribute],
            unsupported_entity_type=None,
            unsupported_evidence_type=goal.required_evidence_type,
            blocking_reason="NO_MATCHING_CAPABILITY",
            explanation="Matching was attempted, but the registry contains no capability for this attribute, entity compatibility, and observation strategy.",
            conflicts=["no_registered_capability"],
            prerequisites=list(strategy.required_preconditions),
            available=False,
        )

    def _arbitration_criteria(self) -> dict[str, Any]:
        return {
            "coverage_contractual": "highest_weight",
            "confidence": "prefer_higher",
            "cost": "prefer_lower",
            "latency": "prefer_lower",
            "availability": "required",
            "risk": "reject_conflicts",
            "determinism": "prefer_deterministic",
        }

    def _match_summary(self, match: CapabilityMatch) -> dict[str, Any]:
        return {
            "match_id": match.match_id,
            "capability_id": match.capability_id,
            "strategy_id": match.strategy_id,
            "score": match.score,
            "conflicts": match.conflicts,
            "attributes_covered": match.attributes_covered,
            "attributes_missing": match.attributes_missing,
        }

    def _goal_attribute(self, goals: list[ObservationGoal], goal_id: str) -> str:
        for goal in goals:
            if goal.goal_id == goal_id:
                return goal.attribute_name
        return ""

    def _strategy_ids_by_goal(self, strategies: list[ObservationStrategy]) -> dict[str, list[str]]:
        rows: dict[str, list[str]] = {}
        for strategy in strategies:
            rows.setdefault(strategy.goal_id, []).append(strategy.strategy_id)
        return rows

    def _match_ids_by_goal(self, matches: list[CapabilityMatch]) -> dict[str, list[str]]:
        rows: dict[str, list[str]] = {}
        for match in matches:
            rows.setdefault(match.goal_id, []).append(match.match_id)
        return rows

    def _decision_capability_ids(self, decision: CapabilityDecision | None, matches: list[CapabilityMatch]) -> list[str]:
        if decision is None:
            return []
        ids = [decision.selected_capability_id] if decision.selected_capability_id else []
        ids.extend(match.capability_id for match in matches if match.goal_id == decision.goal_id)
        return list(dict.fromkeys(str(item) for item in ids if item))

    def _strategy_kind_for_id(self, strategies: list[ObservationStrategy], strategy_id: str | None) -> str | None:
        if not strategy_id:
            return None
        for strategy in strategies:
            if strategy.strategy_id == strategy_id:
                return strategy.strategy_kind
        return None

    def _reason_chain(self, reason: str | None) -> list[str]:
        if not reason:
            return []
        if reason == "NO_MATCHING_CAPABILITY":
            return ["ATTRIBUTE_NOT_OBSERVED", "OBSERVER_CAPABILITY_MISSING", "NO_MATCHING_CAPABILITY"]
        if reason == "CAPABILITY_REJECTED":
            return ["ATTRIBUTE_NOT_OBSERVED", "OBSERVER_CAPABILITY_MISSING", "CAPABILITY_REJECTED"]
        if reason == "LOW_CONFIDENCE":
            return ["ATTRIBUTE_NOT_OBSERVED", "LOW_CONFIDENCE"]
        if reason == "MULTIPLE_CAPABILITIES_AVAILABLE":
            return ["ATTRIBUTE_NOT_OBSERVED", "MULTIPLE_CAPABILITIES_AVAILABLE"]
        if reason == "ATTRIBUTE_VALUE_NOT_OBSERVED":
            return ["ATTRIBUTE_NOT_OBSERVED", "CAPABILITY_MATCHED", "ATTRIBUTE_VALUE_NOT_OBSERVED"]
        if reason.startswith("MEDIA_") or reason.startswith("MUTAGEN_") or reason.startswith("FFPROBE_") or reason.startswith("OBSERVER_"):
            return ["ATTRIBUTE_NOT_OBSERVED", "OBSERVER_EXECUTION", reason, "EVIDENCE_RECORD_MISSING"]
        if reason in {"ENTITY_SELECTION_POLICY_NOT_APPLIED", "ROOT_ROLE_METADATA_MISSING", "ENTITY_SELECTED_FROM_UNCLASSIFIED_ROOT", "WORKSPACE_ROLE_MISMATCH"}:
            return ["ENTITY_SELECTION", reason]
        return ["ATTRIBUTE_NOT_OBSERVED", reason]

    def _recommendation_for_gap_reason(self, reason: str) -> str:
        if reason == "NO_MATCHING_CAPABILITY":
            return "Register a generic capability that can satisfy the observation strategy for the required attribute."
        if reason == "CAPABILITY_REJECTED":
            return "Resolve capability availability, prerequisite, or conflict constraints before observation."
        if reason == "LOW_CONFIDENCE":
            return "Use a higher-confidence capability or gather stronger evidence before observation."
        if reason == "MULTIPLE_CAPABILITIES_AVAILABLE":
            return "Refine arbitration criteria or capability metadata to resolve the tie deterministically."
        if reason == "ATTRIBUTE_VALUE_NOT_OBSERVED":
            return "Execute the selected observer and persist its AttributeObservation result."
        if reason.startswith("MEDIA_") or reason.startswith("MUTAGEN_") or reason.startswith("FFPROBE_") or reason.startswith("OBSERVER_"):
            return "Resolve observer binding, backend availability, dependency, or output evidence before semantic validation."
        if reason in {"ENTITY_SELECTION_POLICY_NOT_APPLIED", "ROOT_ROLE_METADATA_MISSING", "ENTITY_SELECTED_FROM_UNCLASSIFIED_ROOT", "WORKSPACE_ROLE_MISMATCH"}:
            return "Bind the artifact contract to root-role-aware entity selection before rendering collection rows."
        return "Complete contract-driven perception before claiming semantic artifact completeness."

    def _coverage_by_domain(
        self,
        *,
        observation_plan: ObservationPlan,
        observations: list[AttributeObservation],
    ) -> dict[str, Any]:
        goals = len(observation_plan.observation_goals)
        strategies = len(observation_plan.observation_strategies)
        matches = len(observation_plan.capability_matches)
        decisions = len(observation_plan.capability_decisions)
        positive_matches = [
            item
            for item in observation_plan.capability_matches
            if item.match_status == "MATCHED" and item.capability_id and not item.missing_preconditions
        ]
        negative_matches = [item for item in observation_plan.capability_matches if item.match_status == "NO_MATCHING_CAPABILITY"]
        goals_with_match = len({item.goal_id for item in positive_matches})
        selected_decisions = [item for item in observation_plan.capability_decisions if item.status == "selected"]
        observed = [item for item in observations if item.observation_state == "observed"]
        matching_status = (
            "not_applicable"
            if not goals
            else "complete"
            if goals_with_match == goals
            else "blocked"
            if goals_with_match == 0
            else "partial"
        )
        return {
            "observation_goal": {"count": goals, "status": "complete" if goals else "not_applicable"},
            "observation_strategy": {"count": strategies, "status": "complete" if strategies else "not_applicable"},
            "capability_matching": {
                "count": matches,
                "positive_count": len(positive_matches),
                "negative_count": len(negative_matches),
                "goals_with_match": goals_with_match,
                "goals_without_match": max(0, goals - goals_with_match),
                "status": matching_status,
            },
            "capability_arbitration": {
                "count": decisions,
                "selected": len(selected_decisions),
                "status": "complete" if decisions and len(selected_decisions) == decisions else "partial" if decisions else "not_applicable",
            },
            "attribute_observation": {
                "observed": len(observed),
                "total": len(observations),
                "status": "complete" if observations and len(observed) == len(observations) else "partial" if observations else "not_applicable",
            },
        }

    def _attribute_payload(self, entity: dict[str, Any], attribute: str) -> dict[str, Any]:
        canonical = self.observed_entities.canonical_attribute_name(attribute)
        for key in ("observed_attributes", "inferred_attributes"):
            container = entity.get(key) if isinstance(entity.get(key), dict) else {}
            payload = container.get(canonical)
            if isinstance(payload, dict):
                return payload
        return {}

    def _evidence_refs(self, entities: list[dict[str, Any]]) -> list[str]:
        refs: list[str] = []
        for entity in entities[:10]:
            refs.extend(str(ref) for ref in entity.get("evidence_refs") or [] if ref)
        return list(dict.fromkeys(refs))

    def _gap(
        self,
        gap_type: str,
        *,
        reason_code: str,
        expected: Any,
        observed: Any,
        domain: str,
        evidence_refs: list[str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "gap_type": gap_type,
            "reason_code": reason_code,
            "perception_domain": domain,
            "severity": "high",
            "expected": expected,
            "observed": observed,
            "confidence": 1.0,
            "repair_hint": "Complete contract-driven perception before claiming semantic artifact completeness.",
            "evidence_refs": evidence_refs or [],
            "details": details or {},
        }

    def _domain_for_gap_reason(self, reason: str) -> str:
        if reason in {"OBSERVER_CAPABILITY_MISSING", "NO_MATCHING_CAPABILITY"}:
            return "observer_capability"
        if reason in {"CAPABILITY_REJECTED", "MULTIPLE_CAPABILITIES_AVAILABLE", "LOW_CONFIDENCE"}:
            return "capability_arbitration"
        if reason in {
            "ENTITY_SELECTION_EMPTY",
            "ENTITY_AMBIGUOUS",
            "ENTITY_SELECTION_POLICY_NOT_APPLIED",
            "ROOT_ROLE_METADATA_MISSING",
            "ENTITY_SELECTED_FROM_UNCLASSIFIED_ROOT",
            "WORKSPACE_ROLE_MISMATCH",
        }:
            return "entity_selection"
        if reason.startswith("MEDIA_") or reason.startswith("MUTAGEN_") or reason.startswith("FFPROBE_") or reason.startswith("OBSERVER_"):
            return "observer_execution_or_backend"
        return "attribute_observation"

    def _normalize(self, value: Any) -> str:
        normalized = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
        normalized = re.sub(r"[^0-9A-Za-z]+", "_", normalized.casefold())
        return "_".join(part for part in normalized.split("_") if part)
