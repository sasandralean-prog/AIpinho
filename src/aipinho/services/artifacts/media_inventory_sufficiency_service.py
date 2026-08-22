from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from aipinho.services.artifacts.artifact_use_safety_service import ArtifactUseSafetyService


@dataclass(frozen=True)
class MediaInventorySufficiencyPolicy:
    require_complete_selection: bool = True
    require_full_evidence_coverage: bool = True
    require_full_identity_coverage: bool = True
    require_metadata_probe_attempted: bool = True
    require_metadata_observation: bool = True
    max_read_error_ratio: float = 0.0
    max_unsupported_ratio: float = 1.0


@dataclass(frozen=True)
class MediaInventorySufficiencyResult:
    status: str
    reason_code: str | None
    safe_to_use: bool
    use_safety: dict[str, Any]
    coverage_summary: dict[str, Any]
    reason_codes: list[str] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)

    def model_dump(self, *, mode: str = "python") -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "safe_to_use": self.safe_to_use,
            "use_safety": dict(self.use_safety),
            "coverage_summary": dict(self.coverage_summary),
            "reason_codes": list(self.reason_codes),
            "limitations": list(self.limitations),
        }


class MediaInventorySufficiencyService:
    """Evaluates media inventory sufficiency from governed summaries only."""

    def __init__(
        self,
        policy: MediaInventorySufficiencyPolicy | None = None,
        use_safety: ArtifactUseSafetyService | None = None,
    ) -> None:
        self.policy = policy or MediaInventorySufficiencyPolicy()
        self.use_safety = use_safety or ArtifactUseSafetyService()

    def evaluate(
        self,
        *,
        expected_rows: int,
        selected_rows: int,
        bound_rows: int,
        evidence_ref_count: int,
        row_validation: dict[str, Any],
        media_metadata_capability: dict[str, Any],
        metadata_coverage: dict[str, Any],
        schema_status: str,
        row_applicability: dict[str, Any] | None = None,
    ) -> MediaInventorySufficiencyResult:
        expected = max(0, int(expected_rows or 0))
        selected = max(0, int(selected_rows or 0))
        bound = max(0, int(bound_rows or 0))
        evidence_refs = max(0, int(evidence_ref_count or 0))
        row_evidence = row_validation.get("row_evidence_coverage") if isinstance(row_validation.get("row_evidence_coverage"), dict) else {}
        row_identity = row_validation.get("row_identity_coverage") if isinstance(row_validation.get("row_identity_coverage"), dict) else {}
        rendered = max(0, int(row_validation.get("row_count") or 0))
        stable_identity_rows = int(
            row_identity.get("rows_with_stable_entity_identity")
            if row_identity
            else row_validation.get("rows_with_required_identity")
            or 0
        )
        semantic_identity_rows = int(row_identity.get("rows_with_semantic_identity_evidence") or 0)
        stable_identity_ratio = self._ratio(stable_identity_rows, rendered)
        semantic_identity_ratio = self._ratio(semantic_identity_rows, rendered)
        row_applicability = row_applicability if isinstance(row_applicability, dict) else {}
        primary_media_count = int(row_applicability.get("primary_media_row_count") or 0)
        primary_governed_identity_count = int(row_applicability.get("primary_media_with_governed_identity_count") or 0)
        primary_without_identity_count = int(row_applicability.get("primary_media_without_identity_tags_count") or 0)
        primary_backend_no_evidence_count = int(row_applicability.get("primary_media_backend_no_valid_evidence_count") or 0)
        candidate_identity_count = int(row_applicability.get("candidate_identity_available_count") or 0)
        inferred_identity_count = int(row_applicability.get("inferred_identity_available_count") or 0)
        container_mismatch_count = int(row_applicability.get("file_anatomy_extension_container_mismatch_count") or 0)
        sidecar_relationship_count = int(row_applicability.get("sidecar_relationship_candidate_count") or 0)
        artwork_candidate_count = int(row_applicability.get("artwork_candidate_count") or 0)
        inventory_confidence = row_applicability.get("inventory_confidence") if isinstance(row_applicability.get("inventory_confidence"), dict) else {}
        primary_identity_ratio = self._ratio(primary_governed_identity_count, primary_media_count)
        evidence_ratio = self._ratio(int(row_evidence.get("rows_with_evidence_ref") or evidence_refs), selected)
        selection_ratio = self._ratio(selected, expected)
        metadata_ratio = float(
            metadata_coverage.get("primary_media_observation_ratio")
            if row_applicability and metadata_coverage.get("primary_media_observation_ratio") is not None
            else metadata_coverage.get("coverage_ratio")
            or 0.0
        )
        attempted = int(
            metadata_coverage.get("primary_media_files_attempted")
            if row_applicability and metadata_coverage.get("primary_media_files_attempted") is not None
            else metadata_coverage.get("files_attempted")
            or 0
        )
        selected_for_metadata = primary_media_count if row_applicability else selected
        unsupported = int(metadata_coverage.get("unsupported_count") or 0)
        read_errors = int(metadata_coverage.get("read_error_count") or 0)
        reason_codes: list[str] = []
        limitations: list[str] = []
        capability_status = str(media_metadata_capability.get("status") or "not_configured")
        contract_required_missing = media_metadata_capability.get("contract_required_attributes_missing")
        missing_source = contract_required_missing if contract_required_missing is not None else media_metadata_capability.get("attributes_missing", [])
        metadata_attributes_missing = [
            str(item)
            for item in missing_source or []
            if str(item).strip()
        ]
        if expected <= 0:
            reason_codes.append("MEDIA_CORPUS_ENTITY_SELECTION_EMPTY")
        if self.policy.require_complete_selection and expected and selected < expected:
            reason_codes.append("MEDIA_INVENTORY_COVERAGE_INSUFFICIENT")
            limitations.append("inventory_selection_does_not_cover_expected_entities")
        if self.policy.require_full_evidence_coverage and selected and (bound < selected or evidence_ratio < 1.0):
            reason_codes.append("ARTIFACT_EVIDENCE_BINDING_MISSING")
            limitations.append("row_evidence_coverage_incomplete")
        if self.policy.require_full_identity_coverage and rendered and stable_identity_ratio < 1.0:
            reason_codes.append("MEDIA_IDENTITY_BINDING_INCOMPLETE")
            limitations.append("stable_entity_identity_binding_incomplete")
        if row_applicability and self.policy.require_full_identity_coverage and primary_media_count and primary_identity_ratio < 1.0:
            reason_codes.append("MEDIA_PRIMARY_IDENTITY_EVIDENCE_INSUFFICIENT")
            limitations.append("primary_media_semantic_identity_evidence_incomplete")
        elif self.policy.require_full_identity_coverage and rendered and semantic_identity_ratio < 1.0:
            reason_codes.append("MEDIA_IDENTITY_EVIDENCE_INSUFFICIENT")
            limitations.append("semantic_media_identity_evidence_incomplete")
        if row_applicability and primary_without_identity_count > 0:
            reason_codes.append("MEDIA_PRIMARY_IDENTITY_TAGS_ABSENT")
            limitations.append("primary_media_files_without_governed_identity_tags")
        if row_applicability and primary_backend_no_evidence_count > 0:
            reason_codes.append("MEDIA_BACKEND_NO_VALID_EVIDENCE")
            limitations.append("primary_media_files_without_valid_backend_evidence")
        if row_applicability and container_mismatch_count > 0:
            reason_codes.append("MEDIA_CONTAINER_EXTENSION_MISMATCH")
            limitations.append("declared_extension_differs_from_observed_container_signature")
        if row_applicability and candidate_identity_count > 0:
            reason_codes.append("MEDIA_CANDIDATE_IDENTITY_NOT_TRUTH")
            limitations.append("candidate_identity_available_but_not_semantic_truth")
        if row_applicability and inferred_identity_count > 0:
            reason_codes.append("CATALOG_INFERRED_IDENTITY_USED_WITH_LIMITATIONS")
            limitations.append("inferred_identity_available_for_catalog_not_truth")
        if row_applicability and primary_media_count and primary_identity_ratio < 1.0:
            reason_codes.append("CATALOG_OBSERVED_IDENTITY_INCOMPLETE")
            reason_codes.append("CATALOG_NOT_SAFE_FOR_FULL_TRUTH_CLAIM")
            limitations.append("observed_identity_truth_claim_insufficient")
        if inventory_confidence and inventory_confidence.get("safe_for_catalog"):
            reason_codes.append("CATALOG_SAFE_FOR_PLANNING_WITH_LIMITATIONS")
            limitations.append("catalog_representation_safe_for_planning_with_limitations")
        if row_applicability and sidecar_relationship_count > 0:
            reason_codes.append("MEDIA_SIDECAR_RELATIONSHIP_POLICY_REQUIRED")
            limitations.append("lyrics_sidecar_relationship_candidates_require_validation")
        if row_applicability and artwork_candidate_count > 0:
            reason_codes.append("MEDIA_ARTWORK_RELATIONSHIP_POLICY_REQUIRED")
            limitations.append("artwork_candidates_require_relationship_validation")
        if schema_status != "satisfied":
            reason_codes.append("MEDIA_INVENTORY_SCHEMA_INSUFFICIENT")
            limitations.append("schema_or_alias_validation_not_satisfied")
        if self.policy.require_metadata_observation and selected_for_metadata and metadata_ratio < 1.0:
            reason_codes.append("MEDIA_METADATA_OBSERVATION_INCOMPLETE")
            limitations.append("metadata_observation_coverage_below_required_threshold")
        if self.policy.require_metadata_probe_attempted and selected_for_metadata and attempted < selected_for_metadata:
            reason_codes.append("MEDIA_METADATA_PROBE_NOT_RUN")
            limitations.append("metadata_probe_not_attempted_for_all_selected_entities")
        if capability_status in {"not_configured", "missing_dependency", "unavailable"}:
            reason_codes.append("MEDIA_METADATA_CAPABILITY_NOT_CONFIGURED")
            limitations.append(f"media_metadata_capability_{capability_status}")
        elif capability_status in {"blocked", "failed"}:
            reason_codes.append("MEDIA_METADATA_OBSERVATION_INCOMPLETE")
            limitations.append(f"media_metadata_capability_{capability_status}")
        if selected and self._ratio(read_errors, selected) > self.policy.max_read_error_ratio:
            reason_codes.append("MEDIA_METADATA_READ_ERRORS_EXCEED_THRESHOLD")
            limitations.append("metadata_read_error_threshold_exceeded")
        if selected and self._ratio(unsupported, selected) > self.policy.max_unsupported_ratio:
            reason_codes.append("MEDIA_METADATA_UNSUPPORTED_FORMATS_EXCEED_THRESHOLD")
            limitations.append("metadata_unsupported_format_threshold_exceeded")
        reason_codes = list(dict.fromkeys(reason_codes))
        status = "satisfied" if not reason_codes else "blocked"
        safe = status == "satisfied"
        full_truth_claim = safe and not metadata_attributes_missing
        use_safety = self.use_safety.evaluate_catalog_artifact(
            inventory_confidence=inventory_confidence,
            reason_codes=reason_codes,
            limitations=limitations,
        )
        phase1_discovery_safe = bool(use_safety.get("safe_for_catalog"))
        return MediaInventorySufficiencyResult(
            status=status,
            reason_code=None if safe else reason_codes[0],
            safe_to_use=safe,
            use_safety={
                "unrestricted": safe,
                "phase1_discovery": phase1_discovery_safe,
                "downstream_static_analysis": use_safety.get("safe_for_downstream_static_analysis"),
                "full_truth_claim": full_truth_claim,
                "limited_truth_claim": safe,
                "safe_for_truth_claim": use_safety.get("safe_for_truth_claim"),
                "safe_for_catalog": use_safety.get("safe_for_catalog"),
                "safe_for_planning": use_safety.get("safe_for_planning"),
                "safe_for_downstream_static_analysis": use_safety.get("safe_for_downstream_static_analysis"),
                "safe_for_destructive_action": use_safety.get("safe_for_destructive_action"),
                "safe_for_user_report": use_safety.get("safe_for_user_report"),
                "validation_status_for_truth_claim": "passed" if use_safety.get("safe_for_truth_claim") is True else "blocked",
                "validation_status_for_catalog": "passed" if use_safety.get("safe_for_catalog") is True else "blocked",
                "validation_status_for_planning": "passed_with_limitations"
                if use_safety.get("safe_for_planning") == "true_with_limitations"
                else "passed"
                if use_safety.get("safe_for_planning") is True
                else "blocked",
                "artifact_safe_for_truth_claim": use_safety.get("safe_for_truth_claim"),
                "artifact_safe_for_catalog": use_safety.get("safe_for_catalog"),
                "artifact_safe_for_planning": use_safety.get("safe_for_planning"),
                "observed_identity_truth_claim_insufficient": use_safety.get("observed_identity_truth_claim_insufficient"),
                "catalog_complete_with_inferred_unknown_status": use_safety.get("catalog_complete_with_inferred_unknown_status"),
                "planning_safe_with_limitations": use_safety.get("planning_safe_with_limitations"),
                "reason_codes": reason_codes,
                "limitations": [
                    *limitations,
                    *(["metadata_fields_missing_for_full_truth_claim"] if safe and metadata_attributes_missing else []),
                ],
            },
            coverage_summary={
                "expected_entities": expected,
                "selected_entities": selected,
                "bound_rows": bound,
                "rows_rendered": rendered if rendered else selected,
                "rows_with_evidence_ref": int(row_evidence.get("rows_with_evidence_ref") or evidence_refs),
                "evidence_ref_count": evidence_refs,
                "rows_with_required_identity": stable_identity_rows,
                "rows_with_stable_entity_identity": stable_identity_rows,
                "rows_with_semantic_identity_evidence": semantic_identity_rows,
                "rows_without_semantic_identity_evidence": int(row_identity.get("rows_without_semantic_identity_evidence") or 0),
                "selection_coverage_ratio": round(selection_ratio, 4),
                "evidence_coverage_ratio": round(evidence_ratio, 4),
                "identity_coverage_ratio": round(stable_identity_ratio, 4),
                "stable_entity_identity_ratio": round(stable_identity_ratio, 4),
                "semantic_identity_evidence_ratio": round(semantic_identity_ratio, 4),
                "primary_media_row_count": primary_media_count,
                "lyrics_sidecar_row_count": int(row_applicability.get("lyrics_sidecar_row_count") or 0),
                "artwork_row_count": int(row_applicability.get("artwork_row_count") or 0),
                "primary_media_with_governed_identity_count": primary_governed_identity_count,
                "primary_media_without_identity_tags_count": primary_without_identity_count,
                "primary_media_backend_no_valid_evidence_count": primary_backend_no_evidence_count,
                "primary_media_identity_ratio": round(primary_identity_ratio, 4),
                "sidecar_relationship_candidate_count": sidecar_relationship_count,
                "artwork_candidate_count": artwork_candidate_count,
                "candidate_identity_available_count": candidate_identity_count,
                "candidate_identity_not_truth_count": int(row_applicability.get("candidate_identity_not_truth_count") or 0),
                "inferred_identity_available_count": inferred_identity_count,
                "rows_observed_identity": int(row_applicability.get("rows_observed_identity") or 0),
                "rows_inferred_identity": int(row_applicability.get("rows_inferred_identity") or 0),
                "rows_candidate_identity": int(row_applicability.get("rows_candidate_identity") or 0),
                "rows_unknown_identity": int(row_applicability.get("rows_unknown_identity") or 0),
                "rows_not_applicable_identity": int(row_applicability.get("rows_not_applicable_identity") or 0),
                "rows_unsupported_identity": int(row_applicability.get("rows_unsupported_identity") or 0),
                "rows_container_mismatch": int(row_applicability.get("rows_container_mismatch") or 0),
                "inventory_confidence": dict(inventory_confidence),
                "technical_metadata_observed_count": int(row_applicability.get("technical_metadata_observed_count") or 0),
                "technical_metadata_only_count": int(row_applicability.get("technical_metadata_only_count") or 0),
                "file_anatomy_extension_container_mismatch_count": container_mismatch_count,
                "row_class_counts": dict(row_applicability.get("row_class_counts") or {}),
                "identity_status": row_identity.get("status") if row_identity else None,
                "identity_reason_code": row_identity.get("reason_code") if row_identity else None,
                "identity_observed_semantic_fields": list(row_identity.get("observed_semantic_identity_fields") or []),
                "identity_locator_context_fields": list(row_identity.get("locator_context_fields") or []),
                "identity_routing_hint_fields": list(row_identity.get("routing_hint_fields") or []),
                "metadata_observation_ratio": round(metadata_ratio, 4),
                "metadata_status": capability_status,
                "metadata_files_attempted": attempted,
                "metadata_files_succeeded": int(metadata_coverage.get("files_succeeded") or 0),
                "metadata_files_failed": int(metadata_coverage.get("files_failed") or 0),
                "unsupported_count": unsupported,
                "read_error_count": read_errors,
                "schema_status": schema_status,
            },
            reason_codes=reason_codes,
            limitations=list(dict.fromkeys(limitations)),
        )

    def _ratio(self, numerator: int, denominator: int) -> float:
        return 1.0 if denominator <= 0 and numerator <= 0 else max(0.0, min(1.0, numerator / max(1, denominator)))
