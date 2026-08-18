from __future__ import annotations

from typing import Any

from aipinho.schemas.artifacts.relationship import (
    RelationshipValidationPolicy,
    RelationshipValidationResult,
)


class RelationshipValidationPolicyService:
    """Evaluates relationship candidate readiness without promoting it to Truth."""

    def validate_many(
        self,
        *,
        relationship_observations: list[dict[str, Any]],
        provenance_traces: list[dict[str, Any]] | None = None,
        evidence_records: list[dict[str, Any]] | None = None,
        policy: RelationshipValidationPolicy | dict[str, Any] | None = None,
    ) -> list[RelationshipValidationResult]:
        validation_policy = self._policy(policy)
        traces_by_id = {
            str(item.get("trace_id")): item
            for item in (provenance_traces or [])
            if isinstance(item, dict) and item.get("trace_id")
        }
        relationship_records = [
            item
            for item in (evidence_records or [])
            if isinstance(item, dict) and item.get("evidence_type") == "relationship_observation"
        ]
        ambiguity = self._ambiguity(relationship_observations)
        results: list[RelationshipValidationResult] = []
        for observation in relationship_observations:
            if not isinstance(observation, dict):
                continue
            results.append(
                self.validate_observation(
                    observation,
                    traces_by_id=traces_by_id,
                    evidence_records=relationship_records,
                    ambiguity=ambiguity,
                    policy=validation_policy,
                )
            )
        return results

    def validate_observation(
        self,
        observation: dict[str, Any],
        *,
        traces_by_id: dict[str, dict[str, Any]],
        evidence_records: list[dict[str, Any]],
        ambiguity: dict[str, set[str]],
        policy: RelationshipValidationPolicy,
    ) -> RelationshipValidationResult:
        candidate_id = str(observation.get("candidate_id") or "")
        trace_id = str(observation.get("provenance_trace_id") or "")
        confidence_model = observation.get("confidence_model") if isinstance(observation.get("confidence_model"), dict) else {}
        signal_contributions = [
            item
            for item in confidence_model.get("signal_contributions", []) or []
            if isinstance(item, dict)
        ]
        signal_types = [str(item.get("signal_type") or "") for item in signal_contributions if item.get("signal_type")]
        unique_signal_types = sorted(set(signal_types))
        confidence = float(observation.get("confidence") or confidence_model.get("normalized_score") or 0.0)
        conflicts = [item for item in observation.get("conflicts", []) or [] if isinstance(item, dict)]
        negative_evidence = [item for item in observation.get("negative_evidence", []) or [] if isinstance(item, dict)]
        negative_total = sum(float(item.get("confidence_penalty") or 0.0) for item in negative_evidence)
        trace = traces_by_id.get(trace_id)
        matching_records = self._matching_records(observation, evidence_records)

        missing_requirements: list[str] = []
        reason_codes: list[str] = []
        signals_failed: list[str] = []
        limitations = list(observation.get("limitations") or [])
        provenance_ok = bool(trace_id and trace)
        evidence_ok = bool(observation.get("evidence_refs"))

        if not provenance_ok:
            missing_requirements.append("provenance_trace_id")
            reason_codes.append("RELATIONSHIP_PROVENANCE_MISSING")
        if not evidence_ok or not matching_records:
            missing_requirements.append("canonical_relationship_evidence_record")
            reason_codes.append("RELATIONSHIP_CANONICAL_EVIDENCE_RECORD_MISSING")
        if len(unique_signal_types) < policy.minimum_signal_diversity:
            missing_requirements.append("minimum_signal_diversity")
            reason_codes.append("RELATIONSHIP_SIGNAL_DIVERSITY_INSUFFICIENT")
        if confidence < policy.minimum_confidence:
            missing_requirements.append("minimum_confidence")
            reason_codes.append("RELATIONSHIP_CONFIDENCE_POLICY_FAILED")
        for required_signal in policy.required_positive_signal_types:
            if required_signal not in unique_signal_types:
                missing_requirements.append(f"required_signal:{required_signal}")
                signals_failed.append(required_signal)
                reason_codes.append("RELATIONSHIP_REQUIRED_SIGNAL_MISSING")
        if negative_total > policy.negative_evidence_threshold:
            reason_codes.append("RELATIONSHIP_NEGATIVE_EVIDENCE_THRESHOLD_EXCEEDED")

        blocking_conflicts = [
            item
            for item in conflicts
            if item.get("blocks_validation_ready", True)
            or str(item.get("code") or "") in set(policy.forbidden_conflicts)
        ]
        if blocking_conflicts:
            reason_codes.append("RELATIONSHIP_CONFLICT_BLOCKED")

        source_id = str(observation.get("source_entity_id") or "")
        target_id = str(observation.get("target_entity_id") or "")
        ambiguous = (
            bool(source_id and source_id in ambiguity["one_source_many_targets"])
            or bool(target_id and target_id in ambiguity["many_sources_one_target"])
        )
        if ambiguous and not bool(policy.ambiguity_policy.get("allow_ambiguous")):
            reason_codes.append("RELATIONSHIP_AMBIGUITY_UNRESOLVED")

        if blocking_conflicts:
            status = "conflicted"
        elif ambiguous and not bool(policy.ambiguity_policy.get("allow_ambiguous")):
            status = "blocked"
        elif missing_requirements or negative_total > policy.negative_evidence_threshold:
            status = "not_ready"
        elif policy.allow_validated_status:
            status = "validated"
        else:
            status = "validation_ready"

        if status in {"validation_ready", "validated"}:
            reason_codes.append("RELATIONSHIP_VALIDATION_READY" if status == "validation_ready" else "RELATIONSHIP_VALIDATED_BY_POLICY")
        else:
            limitations.append("relationship_not_ready_for_final_validation")

        return RelationshipValidationResult(
            candidate_id=candidate_id,
            status=status,
            reason_codes=list(dict.fromkeys(reason_codes)),
            confidence=confidence,
            policy_id=policy.policy_id,
            signals_passed=unique_signal_types,
            signals_failed=list(dict.fromkeys(signals_failed)),
            missing_requirements=list(dict.fromkeys(missing_requirements)),
            conflicts=conflicts,
            negative_evidence=negative_evidence,
            provenance_ok=provenance_ok,
            evidence_ok=evidence_ok,
            truth_eligible=False,
            speaker_claim_allowed=False,
            limitations=list(dict.fromkeys(str(item) for item in limitations if item)),
        )

    def summary(self, results: list[RelationshipValidationResult]) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        reason_codes: list[str] = []
        for result in results:
            by_status[result.status] = by_status.get(result.status, 0) + 1
            reason_codes.extend(result.reason_codes)
        return {
            "status": "available" if results else "not_available",
            "result_count": len(results),
            "by_status": by_status,
            "validation_ready_count": by_status.get("validation_ready", 0),
            "validated_relationship_count": by_status.get("validated", 0),
            "blocked_relationship_count": by_status.get("blocked", 0),
            "conflicted_relationship_count": by_status.get("conflicted", 0),
            "truth_eligible_relationship_count": 0,
            "reason_codes": list(dict.fromkeys(reason_codes)),
            "truth_eligible": False,
            "speaker_claim_allowed": False,
        }

    def _policy(self, policy: RelationshipValidationPolicy | dict[str, Any] | None) -> RelationshipValidationPolicy:
        if isinstance(policy, RelationshipValidationPolicy):
            return policy
        if isinstance(policy, dict):
            return RelationshipValidationPolicy(**policy)
        return RelationshipValidationPolicy()

    def _matching_records(self, observation: dict[str, Any], evidence_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        candidate_id = str(observation.get("candidate_id") or "")
        observation_id = str(observation.get("observation_id") or "")
        evidence_refs = {str(item) for item in observation.get("evidence_refs", []) or [] if item}
        rows: list[dict[str, Any]] = []
        for record in evidence_records:
            if candidate_id and str(record.get("candidate_id") or "") == candidate_id:
                rows.append(record)
                continue
            if observation_id and str(record.get("observation_id") or "") == observation_id:
                rows.append(record)
                continue
            if evidence_refs and str(record.get("evidence_id") or "") in evidence_refs:
                rows.append(record)
        return rows

    def _ambiguity(self, observations: list[dict[str, Any]]) -> dict[str, set[str]]:
        targets_by_source: dict[str, set[str]] = {}
        sources_by_target: dict[str, set[str]] = {}
        for observation in observations:
            if not isinstance(observation, dict):
                continue
            source_id = str(observation.get("source_entity_id") or "")
            target_id = str(observation.get("target_entity_id") or "")
            if source_id and target_id:
                targets_by_source.setdefault(source_id, set()).add(target_id)
                sources_by_target.setdefault(target_id, set()).add(source_id)
        return {
            "one_source_many_targets": {source for source, targets in targets_by_source.items() if len(targets) > 1},
            "many_sources_one_target": {target for target, sources in sources_by_target.items() if len(sources) > 1},
        }
