from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from aipinho.schemas.artifacts.contract_perception import EvidenceRecord, EvidenceSet
from aipinho.schemas.artifacts.relationship import (
    RelationshipCandidate,
    RelationshipConfidenceModel,
    RelationshipConflict,
    RelationshipEvidence,
    RelationshipEvidenceSignal,
    RelationshipGoal,
    RelationshipNegativeEvidence,
    RelationshipObservation,
    RelationshipProvenanceTrace,
)


MEDIA_RELATIONSHIP_CAPABILITY_ID = "media_relationship_candidate_detector"


class MediaRelationshipCandidateService:
    """Produces relationship candidates from generic evidence signals.

    This service is intentionally conservative: it creates candidate/evidence
    objects only. It does not validate final relationships and does not make
    extension-specific authority decisions.
    """

    def detect(
        self,
        *,
        entities: list[dict[str, Any]],
        relationship_goal: RelationshipGoal,
        artifact_contract: dict[str, Any] | None = None,
        producer_capability_id: str = MEDIA_RELATIONSHIP_CAPABILITY_ID,
    ) -> dict[str, Any]:
        eligible, rejected = self._eligible_entities(entities)
        candidates: list[RelationshipCandidate] = []
        evidence: list[RelationshipEvidence] = []
        observations: list[RelationshipObservation] = []
        evidence_records: list[EvidenceRecord] = []
        provenance_traces: list[RelationshipProvenanceTrace] = []
        if not relationship_goal:
            return self._empty_summary("NO_RELATIONSHIP_GOAL", rejected=rejected)
        if len(eligible) < 2:
            return self._empty_summary("NO_OBSERVED_ENTITIES", rejected=rejected)

        for index, source in enumerate(eligible):
            for target in eligible[index + 1:]:
                signals = self._signals(source, target, relationship_goal=relationship_goal, artifact_contract=artifact_contract or {})
                strong_signals = [item for item in signals if item.confidence_contribution > 0.0]
                if len(strong_signals) < 2:
                    continue
                candidate_id = f"relationship_candidate_{uuid4().hex}"
                negative_evidence = self._negative_evidence(
                    candidate_id=candidate_id,
                    source=source,
                    target=target,
                    signals=strong_signals,
                )
                conflicts = self._conflicts(
                    candidate_id=candidate_id,
                    source=source,
                    target=target,
                    signals=strong_signals,
                )
                confidence_model = self._confidence_model(
                    signals=strong_signals,
                    negative_evidence=negative_evidence,
                    conflicts=conflicts,
                    minimum_candidate_confidence=float(relationship_goal.confidence_policy.get("minimum_candidate_confidence", 0.35)),
                )
                score = confidence_model.normalized_score
                if score < float(relationship_goal.confidence_policy.get("minimum_candidate_confidence", 0.35)) and not conflicts:
                    continue
                relationship_evidence: list[RelationshipEvidence] = []
                for signal in strong_signals:
                    item = RelationshipEvidence(
                        candidate_id=candidate_id,
                        signal_id=signal.signal_id,
                        signal_type=signal.signal_type,
                        signal_value=signal.normalized_value,
                        source_entity_id=str(source.get("entity_id") or ""),
                        target_entity_id=str(target.get("entity_id") or ""),
                        confidence_contribution=signal.confidence_contribution,
                        provenance=signal.provenance,
                        is_sufficient_alone=False,
                        limitations=list(signal.limitations),
                        negative_evidence=[item.model_dump(mode="json") for item in negative_evidence],
                        conflicts=[item.model_dump(mode="json") for item in conflicts],
                    )
                    relationship_evidence.append(item)
                    evidence.append(item)
                relation_family = self._relation_family(source, target, strong_signals, relationship_goal)
                relation_kind = self._relation_kind_candidate(relation_family, strong_signals)
                trace = self._provenance_trace(
                    candidate_id=candidate_id,
                    source=source,
                    target=target,
                    producer_capability_id=producer_capability_id,
                    relationship_goal=relationship_goal,
                    artifact_contract=artifact_contract or {},
                    signals_used=strong_signals,
                    signals_rejected=[item for item in signals if item.confidence_contribution <= 0.0],
                    evidence_refs=[item.evidence_id for item in relationship_evidence],
                    conflicts=conflicts,
                    negative_evidence=negative_evidence,
                )
                provenance_traces.append(trace)
                reason_codes = ["RELATIONSHIP_CANDIDATE_OBSERVED", "RELATIONSHIP_EVIDENCE_PRESENT", "RELATIONSHIP_PROVENANCE_PRESENT", "RELATIONSHIP_VALIDATION_REQUIRED"]
                if negative_evidence:
                    reason_codes.append("RELATIONSHIP_NEGATIVE_EVIDENCE_PRESENT")
                if conflicts:
                    reason_codes.append("RELATIONSHIP_CONFLICT_PRESENT")
                candidate = RelationshipCandidate(
                    candidate_id=candidate_id,
                    source_entity_id=str(source.get("entity_id") or ""),
                    target_entity_id=str(target.get("entity_id") or ""),
                    relation_family=relation_family,
                    relation_kind_candidate=relation_kind,
                    status="candidate",
                    confidence=round(score, 4),
                    confidence_band=confidence_model.confidence_band,
                    confidence_model=confidence_model,
                    evidence_refs=[item.evidence_id for item in relationship_evidence],
                    provenance_trace_id=trace.trace_id,
                    provenance={
                        "source": "media_relationship_candidate_detector",
                        "producer_capability_id": producer_capability_id,
                        "source_entity_ref": self._entity_ref(source),
                        "target_entity_ref": self._entity_ref(target),
                        "signal_types": [item.signal_type for item in strong_signals],
                        "provenance_trace_id": trace.trace_id,
                    },
                    limitations=[
                        "relationship_candidate_requires_later_validation",
                        "no_single_signal_is_sufficient_authority",
                    ],
                    negative_evidence=negative_evidence,
                    conflicts=conflicts,
                    reason_codes=list(dict.fromkeys(reason_codes)),
                    truth_eligible=False,
                    validation_required=True,
                )
                observation = RelationshipObservation(
                    candidate_id=candidate.candidate_id,
                    observed_relation_family=candidate.relation_family,
                    observed_relation_kind_candidate=candidate.relation_kind_candidate,
                    evidence_refs=candidate.evidence_refs,
                    provenance_trace_id=trace.trace_id,
                    confidence=candidate.confidence,
                    confidence_model=confidence_model,
                    coverage=min(1.0, len(strong_signals) / 4),
                    producer_capability_id=producer_capability_id,
                    observer_id=None,
                    negative_evidence=[item.model_dump(mode="json") for item in negative_evidence],
                    conflicts=[item.model_dump(mode="json") for item in conflicts],
                    truth_eligible=False,
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
                record = self._evidence_record(
                    candidate=candidate,
                    observation=observation,
                    evidence=relationship_evidence,
                    provenance_trace=trace,
                    source=source,
                    target=target,
                    producer_capability_id=producer_capability_id,
                )
                trace.evidence_record_refs.append(record.evidence_id)
                candidates.append(candidate)
                observations.append(observation)
                evidence_records.append(record)

        reason_codes = ["RELATIONSHIP_CANDIDATE_OBSERVED"] if candidates else ["INSUFFICIENT_EVIDENCE_SIGNALS"]
        return {
            "status": "available" if candidates else "blocked",
            "capability_id": producer_capability_id,
            "relationship_goal": relationship_goal,
            "candidates": candidates,
            "evidence": evidence,
            "observations": observations,
            "evidence_records": evidence_records,
            "provenance_traces": provenance_traces,
            "coverage_summary": {
                "eligible_entity_count": len(eligible),
                "rejected_entity_count": len(rejected),
                "candidate_count": len(candidates),
                "observation_count": len(observations),
                "evidence_count": len(evidence),
                "truth_eligible": False,
                "conflict_count": sum(len(item.conflicts) for item in candidates),
                "negative_evidence_count": sum(len(item.negative_evidence) for item in candidates),
            },
            "limitations": ["relationship_candidates_are_not_final_truth"],
            "reason_codes": reason_codes,
        }

    def evidence_set(self, records: list[EvidenceRecord]) -> EvidenceSet:
        return EvidenceSet(
            records=records,
            entity_refs=[record.source_entity_ref for record in records if record.source_entity_ref],
            attribute_names=[],
            canonical_keys=[],
            coverage_summary={"relationship_observation_count": len(records), "truth_eligible": False},
            confidence_summary=self._confidence_summary([record.confidence for record in records]),
        )

    def _eligible_entities(self, entities: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        eligible: list[dict[str, Any]] = []
        rejected: list[dict[str, Any]] = []
        excluded_roles = {"project_source_file", "build_output_file", "cache_file", "generated_file"}
        excluded_roots = {"project_root", "source_code_root", "build_output_root", "cache_root", "generated_root"}
        allowed_roots = {"library_root", "corpus_root", "external_root", "unknown_root", ""}
        for entity in entities:
            role = str(entity.get("entity_role") or self._attribute_payload(entity, "entity_role").get("value") or "")
            root_role = str(entity.get("source_root_role") or self._attribute_payload(entity, "source_root_role").get("value") or "")
            reasons = list(entity.get("relationship_exclusion_reasons") or [])
            reasons.extend(str(item) for item in entity.get("exclusion_reasons") or [])
            if role in excluded_roles:
                reasons.append("ENTITY_ROLE_NOT_RELATIONSHIP_ELIGIBLE")
            if root_role in excluded_roots:
                reasons.append("SOURCE_ROOT_ROLE_NOT_RELATIONSHIP_ELIGIBLE")
            if root_role and root_role not in allowed_roots:
                reasons.append("SOURCE_ROOT_ROLE_UNKNOWN_FOR_RELATIONSHIP")
            if reasons:
                rejected.append({"entity": entity, "relationship_exclusion_reasons": list(dict.fromkeys(reasons))})
                continue
            if not self._entity_path(entity):
                rejected.append({"entity": entity, "relationship_exclusion_reasons": ["ENTITY_PATH_MISSING"]})
                continue
            eligible.append(entity)
        return eligible, rejected

    def _signals(
        self,
        source: dict[str, Any],
        target: dict[str, Any],
        *,
        relationship_goal: RelationshipGoal,
        artifact_contract: dict[str, Any],
    ) -> list[RelationshipEvidenceSignal]:
        source_path = self._entity_path(source)
        target_path = self._entity_path(target)
        source_stem = self._normalized_stem(source_path)
        target_stem = self._normalized_stem(target_path)
        source_parent = str(Path(source_path).parent).casefold()
        target_parent = str(Path(target_path).parent).casefold()
        source_role = str(source.get("entity_role") or self._attribute_payload(source, "entity_role").get("value") or "")
        target_role = str(target.get("entity_role") or self._attribute_payload(target, "entity_role").get("value") or "")
        source_root_role = str(source.get("source_root_role") or self._attribute_payload(source, "source_root_role").get("value") or "")
        target_root_role = str(target.get("source_root_role") or self._attribute_payload(target, "source_root_role").get("value") or "")
        rows: list[RelationshipEvidenceSignal] = []
        similarity = self._similarity(source_stem, target_stem)
        if similarity >= 0.72:
            rows.append(self._signal("normalized_stem_similarity", {"source": source_stem, "target": target_stem, "similarity": similarity}, round(0.25 * similarity, 4), source, target))
        if source_parent and source_parent == target_parent:
            rows.append(self._signal("same_directory_context", {"directory": source_parent}, 0.22, source, target))
        elif source_parent and target_parent and (source_parent in target_parent or target_parent in source_parent):
            rows.append(self._signal("near_directory_context", {"source_directory": source_parent, "target_directory": target_parent}, 0.12, source, target))
        if source_root_role and target_root_role and source_root_role == target_root_role:
            rows.append(self._signal("source_root_role_compatibility", source_root_role, 0.16, source, target))
        if source_role and target_role and source_role != target_role:
            rows.append(self._signal("entity_role_compatibility", {"source_role": source_role, "target_role": target_role}, 0.12, source, target))
        if artifact_contract.get("expected_relationships") or relationship_goal.allowed_relation_families:
            rows.append(self._signal("artifact_contract_relevance", {"contract_id": artifact_contract.get("contract_id"), "allowed_relation_families": relationship_goal.allowed_relation_families}, 0.12, source, target))
        token_overlap = self._token_overlap(source_stem, target_stem)
        if token_overlap > 0.0 and similarity < 0.72:
            rows.append(self._signal("filename_token_overlap", {"source": source_stem, "target": target_stem, "overlap": token_overlap}, round(0.1 * token_overlap, 4), source, target))
        return rows

    def _signal(self, signal_type: str, value: Any, confidence: float, source: dict[str, Any], target: dict[str, Any]) -> RelationshipEvidenceSignal:
        return RelationshipEvidenceSignal(
            signal_type=signal_type,
            raw_value=value,
            normalized_value=value,
            normalization_trace=["generic_relationship_signal", "no_signal_is_sufficient_alone"],
            source_entity_ref=self._entity_ref(source),
            target_entity_ref=self._entity_ref(target),
            confidence_contribution=confidence,
            confidence_weight=1.0,
            confidence_method="weighted_signal_contribution",
            why_it_matters=f"{signal_type} can support a relationship candidate when combined with other compatible signals.",
            provenance={
                "source_entity_id": source.get("entity_id"),
                "target_entity_id": target.get("entity_id"),
                "source": "ObservedEntity",
            },
            limitations=["candidate_signal_only", "requires_later_validation"],
            negative_evidence=[],
            conflicts=[],
            is_sufficient_alone=False,
        )

    def _negative_evidence(
        self,
        *,
        candidate_id: str,
        source: dict[str, Any],
        target: dict[str, Any],
        signals: list[RelationshipEvidenceSignal],
    ) -> list[RelationshipNegativeEvidence]:
        rows: list[RelationshipNegativeEvidence] = []
        signal_types = {item.signal_type for item in signals}
        source_root_role = str(source.get("source_root_role") or self._attribute_payload(source, "source_root_role").get("value") or "")
        target_root_role = str(target.get("source_root_role") or self._attribute_payload(target, "source_root_role").get("value") or "")
        source_role = str(source.get("entity_role") or self._attribute_payload(source, "entity_role").get("value") or "")
        target_role = str(target.get("entity_role") or self._attribute_payload(target, "entity_role").get("value") or "")
        if source_root_role and target_root_role and source_root_role != target_root_role:
            rows.append(self._negative(candidate_id, "source_root_role_incompatible", 0.18, source, target))
        if source_role and target_role and source_role == target_role:
            rows.append(self._negative(candidate_id, "entity_role_incompatible", 0.08, source, target))
        if len(signal_types) < 2:
            rows.append(self._negative(candidate_id, "insufficient_signal_diversity", 0.2, source, target))
        return rows

    def _conflicts(
        self,
        *,
        candidate_id: str,
        source: dict[str, Any],
        target: dict[str, Any],
        signals: list[RelationshipEvidenceSignal],
    ) -> list[RelationshipConflict]:
        rows: list[RelationshipConflict] = []
        source_root_role = str(source.get("source_root_role") or self._attribute_payload(source, "source_root_role").get("value") or "")
        target_root_role = str(target.get("source_root_role") or self._attribute_payload(target, "source_root_role").get("value") or "")
        if source_root_role and target_root_role and source_root_role != target_root_role:
            rows.append(
                RelationshipConflict(
                    candidate_id=candidate_id,
                    code="source_root_role_incompatible",
                    description="Source and target are from incompatible observed root roles for a relationship candidate.",
                    severity="high",
                    blocks_validation_ready=True,
                    source_entity_ref=self._entity_ref(source),
                    target_entity_ref=self._entity_ref(target),
                    provenance={"source": "ObservedEntity.source_root_role"},
                )
            )
        return rows

    def _negative(
        self,
        candidate_id: str,
        code: str,
        penalty: float,
        source: dict[str, Any],
        target: dict[str, Any],
    ) -> RelationshipNegativeEvidence:
        return RelationshipNegativeEvidence(
            candidate_id=candidate_id,
            code=code,
            description=f"{code} reduces confidence but does not by itself decide final relationship truth.",
            confidence_penalty=penalty,
            source_entity_ref=self._entity_ref(source),
            target_entity_ref=self._entity_ref(target),
            provenance={"source": "relationship_policy_check"},
            limitations=["negative_evidence_is_not_final_truth"],
        )

    def _confidence_model(
        self,
        *,
        signals: list[RelationshipEvidenceSignal],
        negative_evidence: list[RelationshipNegativeEvidence],
        conflicts: list[RelationshipConflict],
        minimum_candidate_confidence: float,
    ) -> RelationshipConfidenceModel:
        positive = sum(item.confidence_contribution * item.confidence_weight for item in signals)
        negative = sum(item.confidence_penalty for item in negative_evidence)
        conflict_penalty = 0.25 * len([item for item in conflicts if item.blocks_validation_ready])
        raw = positive - negative - conflict_penalty
        normalized = max(0.0, min(0.95, raw))
        if conflicts:
            band = "conflicted"
        elif normalized < minimum_candidate_confidence:
            band = "insufficient"
        elif normalized >= 0.75:
            band = "high"
        elif normalized >= 0.5:
            band = "medium"
        else:
            band = "low"
        return RelationshipConfidenceModel(
            raw_score=round(raw, 4),
            normalized_score=round(normalized, 4),
            confidence_band=band,
            signal_contributions=[
                {
                    "signal_id": item.signal_id,
                    "signal_type": item.signal_type,
                    "confidence_contribution": item.confidence_contribution,
                    "confidence_weight": item.confidence_weight,
                    "confidence_method": item.confidence_method,
                    "is_sufficient_alone": False,
                }
                for item in signals
            ],
            positive_signal_count=len(signals),
            negative_signal_count=len(negative_evidence),
            conflict_count=len(conflicts),
            missing_signal_count=max(0, 3 - len(signals)),
            calibration_notes=[
                "high_confidence_is_not_truth",
                "relationship_validation_required",
                "conflicted_confidence_blocks_future_promotion",
            ],
            limitations=["confidence_model_is_candidate_readiness_only"],
        )

    def _provenance_trace(
        self,
        *,
        candidate_id: str,
        source: dict[str, Any],
        target: dict[str, Any],
        producer_capability_id: str,
        relationship_goal: RelationshipGoal,
        artifact_contract: dict[str, Any],
        signals_used: list[RelationshipEvidenceSignal],
        signals_rejected: list[RelationshipEvidenceSignal],
        evidence_refs: list[str],
        conflicts: list[RelationshipConflict],
        negative_evidence: list[RelationshipNegativeEvidence],
    ) -> RelationshipProvenanceTrace:
        return RelationshipProvenanceTrace(
            candidate_id=candidate_id,
            source_entity_ref=self._entity_ref(source),
            target_entity_ref=self._entity_ref(target),
            producer_capability_id=producer_capability_id,
            relationship_goal_id=relationship_goal.goal_id,
            input_entities_ref=[self._entity_ref(source), self._entity_ref(target)],
            input_artifact_contract_ref={
                "contract_id": artifact_contract.get("contract_id"),
                "artifact_id": artifact_contract.get("artifact_id"),
                "artifact_logical_path": artifact_contract.get("artifact_logical_path"),
                "expected_relationships_declared": bool(artifact_contract.get("expected_relationships")),
            },
            signals_used=[item.model_dump(mode="json") for item in signals_used],
            signals_rejected=[item.model_dump(mode="json") for item in signals_rejected],
            normalization_steps=[
                {
                    "step": "normalize_stem_and_tokens",
                    "method": "unicode_nfkd_ascii_casefold_tokenize",
                    "source": self._normalized_stem(self._entity_path(source)),
                    "target": self._normalized_stem(self._entity_path(target)),
                }
            ],
            policy_checks=[
                {"code": "single_signal_not_sufficient", "passed": len(signals_used) >= 2},
                {"code": "truth_policy_candidate_only", "passed": not bool((relationship_goal.truth_policy or {}).get("truth_eligible"))},
                {"code": "negative_evidence_checked", "passed": True, "count": len(negative_evidence)},
                {"code": "conflicts_checked", "passed": True, "count": len(conflicts)},
            ],
            arbitration_decision_ref=f"capability:{producer_capability_id}",
            evidence_record_refs=evidence_refs,
            created_at=datetime.now(timezone.utc).isoformat(),
        )

    def _relation_family(self, source: dict[str, Any], target: dict[str, Any], signals: list[RelationshipEvidenceSignal], goal: RelationshipGoal) -> str:
        allowed = [item for item in goal.allowed_relation_families if str(item).strip()]
        if allowed:
            return str(allowed[0])
        roles = " ".join([
            str(source.get("entity_role") or ""),
            str(target.get("entity_role") or ""),
            " ".join(str(item.signal_type) for item in signals),
        ]).casefold()
        if "text" in roles:
            return "textual_sidecar_candidate"
        if "image" in roles or "visual" in roles:
            return "visual_sidecar_candidate"
        if "metadata" in roles:
            return "metadata_sidecar_candidate"
        if "same_directory_context" in roles:
            return "descriptive_sidecar_candidate"
        return "unknown_related_asset_candidate"

    def _relation_kind_candidate(self, relation_family: str, signals: list[RelationshipEvidenceSignal]) -> str:
        signal_types = {item.signal_type for item in signals}
        if "normalized_stem_similarity" in signal_types:
            return "same_stem_candidate"
        if relation_family.endswith("_sidecar_candidate"):
            return "sidecar_candidate_for"
        return "related_variant_candidate"

    def _evidence_record(
        self,
        *,
        candidate: RelationshipCandidate,
        observation: RelationshipObservation,
        evidence: list[RelationshipEvidence],
        provenance_trace: RelationshipProvenanceTrace,
        source: dict[str, Any],
        target: dict[str, Any],
        producer_capability_id: str,
    ) -> EvidenceRecord:
        return EvidenceRecord(
            source="RelationshipObservation",
            acquisition_method="candidate_detection",
            observer_id=None,
            capability_id=producer_capability_id,
            evidence_type="relationship_observation",
            candidate_id=candidate.candidate_id,
            observation_id=observation.observation_id,
            provenance_trace_id=provenance_trace.trace_id,
            entity_ref={"candidate_id": candidate.candidate_id},
            source_entity_ref=self._entity_ref(source),
            target_entity_ref=self._entity_ref(target),
            relation_family=candidate.relation_family,
            relation_kind_candidate=candidate.relation_kind_candidate,
            normalized_value={
                "candidate_id": candidate.candidate_id,
                "relation_family": candidate.relation_family,
                "relation_kind_candidate": candidate.relation_kind_candidate,
                "truth_eligible": False,
                "validation_required": True,
            },
            semantic_type="relationship_observation",
            confidence=observation.confidence,
            signals=[item.model_dump(mode="json") for item in evidence],
            negative_evidence=[item.model_dump(mode="json") for item in candidate.negative_evidence],
            conflicts=[item.model_dump(mode="json") for item in candidate.conflicts],
            provenance=candidate.provenance,
            limitations=list(candidate.limitations),
            truth_eligible=False,
            validation_required=True,
        )

    def _empty_summary(self, reason_code: str, *, rejected: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        return {
            "status": "blocked",
            "capability_id": MEDIA_RELATIONSHIP_CAPABILITY_ID,
            "relationship_goal": None,
            "candidates": [],
            "evidence": [],
            "observations": [],
            "evidence_records": [],
            "provenance_traces": [],
            "coverage_summary": {
                "eligible_entity_count": 0,
                "rejected_entity_count": len(rejected or []),
                "candidate_count": 0,
                "observation_count": 0,
                "evidence_count": 0,
                "truth_eligible": False,
            },
            "limitations": ["relationship_candidate_detection_blocked"],
            "reason_codes": [reason_code],
        }

    def _entity_ref(self, entity: dict[str, Any]) -> dict[str, Any]:
        return {
            "entity_id": entity.get("entity_id"),
            "entity_kind": entity.get("entity_kind"),
            "source": entity.get("source"),
            "relative_path": entity.get("relative_path"),
            "source_root_role": entity.get("source_root_role"),
            "entity_role": entity.get("entity_role"),
        }

    def _entity_path(self, entity: dict[str, Any]) -> str:
        for key in ("relative_path", "source", "path", "name"):
            value = entity.get(key)
            if value:
                return str(value)
        payload = self._attribute_payload(entity, "relative_path") or self._attribute_payload(entity, "name")
        return str(payload.get("value") or "")

    def _normalized_stem(self, path: str) -> str:
        stem = Path(str(path or "")).stem or str(path or "")
        normalized = unicodedata.normalize("NFKD", stem).encode("ascii", "ignore").decode("ascii")
        normalized = re.sub(r"[^0-9A-Za-z]+", " ", normalized.casefold())
        return " ".join(part for part in normalized.split() if part)

    def _token_overlap(self, left: str, right: str) -> float:
        left_tokens = {item for item in left.split() if item}
        right_tokens = {item for item in right.split() if item}
        if not left_tokens or not right_tokens:
            return 0.0
        return len(left_tokens & right_tokens) / max(1, len(left_tokens | right_tokens))

    def _similarity(self, left: str, right: str) -> float:
        if not left or not right:
            return 0.0
        if left == right:
            return 1.0
        overlap = self._token_overlap(left, right)
        prefix = 0.0
        for index, (l_char, r_char) in enumerate(zip(left, right), start=1):
            if l_char != r_char:
                break
            prefix = index / max(len(left), len(right))
        return max(overlap, prefix)

    def _confidence_summary(self, values: list[float]) -> dict[str, Any]:
        if not values:
            return {"count": 0, "max": 0.0, "average": 0.0}
        return {
            "count": len(values),
            "max": round(max(values), 4),
            "average": round(sum(values) / len(values), 4),
        }

    def _attribute_payload(self, entity: dict[str, Any], attribute: str) -> dict[str, Any]:
        for container in ("observed_attributes", "inferred_attributes"):
            values = entity.get(container)
            if isinstance(values, dict) and isinstance(values.get(attribute), dict):
                return values[attribute]
        return {}
