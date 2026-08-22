from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from aipinho.services.artifacts.catalog_confidence_model import CatalogConfidenceScoringService, build_catalog_field
from aipinho.services.artifacts.file_container_signature_service import FileContainerSignatureService
from aipinho.services.artifacts.media_candidate_identity_policy import MediaCandidateIdentityPolicy


PRIMARY_MEDIA_EXTENSIONS = {"m4a", "mp3", "mp4"}
LYRICS_EXTENSIONS = {"lrc"}
ARTWORK_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
IDENTITY_KEYS = {"track_title", "artist", "album", "album_artist"}
TECHNICAL_MEDIA_KEYS = {"codec", "container", "duration", "bitrate", "sample_rate", "channels", "artwork"}


class MediaInventoryRowTaxonomyService:
    """Builds bounded row applicability, candidate identity, and file anatomy summaries."""

    def __init__(
        self,
        *,
        file_container_signatures: FileContainerSignatureService | None = None,
        candidate_identity_policy: MediaCandidateIdentityPolicy | None = None,
        confidence_scoring: CatalogConfidenceScoringService | None = None,
    ) -> None:
        self.file_container_signatures = file_container_signatures or FileContainerSignatureService()
        self.candidate_identity_policy = candidate_identity_policy or MediaCandidateIdentityPolicy()
        self.confidence_scoring = confidence_scoring or CatalogConfidenceScoringService()

    def classify(
        self,
        *,
        selected_entities: list[dict[str, Any]],
        claim_evidence_bindings: dict[str, dict[str, list[dict[str, Any]]]],
        perception_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        perception_payload = perception_payload if isinstance(perception_payload, dict) else {}
        media_observations_by_entity = self._media_observations_by_entity(perception_payload)
        audio_entities = [entity for entity in selected_entities if self._extension(entity) in PRIMARY_MEDIA_EXTENSIONS]
        audio_by_stem = self._audio_index(audio_entities)
        lrc_match_counts: Counter[str] = Counter()
        precomputed_lrc_matches: dict[str, dict[str, Any]] = {}
        for entity in selected_entities:
            if self._extension(entity) not in LYRICS_EXTENSIONS:
                continue
            relationship = self._lyrics_relationship(entity, audio_by_stem=audio_by_stem)
            precomputed_lrc_matches[str(entity.get("entity_id") or "")] = relationship
            audio_id = str(relationship.get("likely_audio_entity_id") or "")
            if audio_id:
                lrc_match_counts[audio_id] += 1

        rows_by_entity: dict[str, dict[str, Any]] = {}
        row_class_counts: Counter[str] = Counter()
        anatomy_counts: Counter[str] = Counter()
        candidate_count = 0
        technical_observed_count = 0
        technical_only_count = 0
        sidecar_relationship_count = 0
        anatomy_mismatch_count = 0
        backend_no_valid_evidence_count = 0
        inferred_identity_count = 0
        low_candidate_identity_count = 0
        unknown_identity_count = 0
        not_applicable_identity_count = 0
        unsupported_identity_count = 0
        read_error_identity_count = 0
        container_mismatch_identity_count = 0
        safe_for_catalog_count = 0
        safe_for_planning_count = 0
        safe_for_truth_claim_count = 0
        catalog_status_counts: Counter[str] = Counter()
        identity_status_counts: Counter[str] = Counter()
        score_sums: Counter[str] = Counter()

        for entity in selected_entities:
            entity_id = str(entity.get("entity_id") or "")
            if not entity_id:
                continue
            extension = self._extension(entity)
            observed_identity = self._observed_identity_values(entity_id, claim_evidence_bindings)
            identity_observed = bool(observed_identity)
            observations = media_observations_by_entity.get(entity_id, [])
            technical_observed = self._has_technical_metadata(observations)
            anatomy = self.file_container_signatures.observe_entity(entity)
            candidate = self.candidate_identity_policy.evaluate(entity)
            relationship = precomputed_lrc_matches.get(entity_id) if extension in LYRICS_EXTENSIONS else {}
            if relationship and relationship.get("likely_audio_entity_id"):
                sidecar_relationship_count += 1
            if relationship and lrc_match_counts[str(relationship.get("likely_audio_entity_id") or "")] > 1:
                flags = list(relationship.get("risk_flags") or [])
                if "LYRICS_SIDECAR_SUSPICIOUS_COLLISION" not in flags:
                    flags.append("LYRICS_SIDECAR_SUSPICIOUS_COLLISION")
                relationship["risk_flags"] = flags

            if extension in PRIMARY_MEDIA_EXTENSIONS:
                if identity_observed:
                    row_class = "primary_media_with_governed_identity"
                    sufficiency_status = "satisfied"
                    reason_code = None
                elif technical_observed:
                    row_class = "primary_media_without_identity_tags"
                    sufficiency_status = "blocked"
                    reason_code = "MEDIA_PRIMARY_IDENTITY_TAGS_ABSENT"
                else:
                    row_class = "primary_media_backend_no_valid_evidence"
                    sufficiency_status = "blocked"
                    reason_code = (
                        "MEDIA_CONTAINER_EXTENSION_MISMATCH"
                        if anatomy.get("extension_container_mismatch")
                        else "MEDIA_BACKEND_NO_VALID_EVIDENCE"
                    )
                    backend_no_valid_evidence_count += 1
            elif extension in LYRICS_EXTENSIONS:
                row_class = "lyrics_sidecar_candidate"
                sufficiency_status = "relationship_policy_required"
                reason_code = "MEDIA_SIDECAR_RELATIONSHIP_POLICY_REQUIRED"
            elif extension in ARTWORK_EXTENSIONS:
                row_class = "artwork_candidate"
                sufficiency_status = "relationship_policy_required"
                reason_code = "MEDIA_ARTWORK_RELATIONSHIP_POLICY_REQUIRED"
            elif extension:
                row_class = "non_primary_corpus_member"
                sufficiency_status = "not_primary_media"
                reason_code = None
            else:
                row_class = "unknown_or_unclassified"
                sufficiency_status = "unknown"
                reason_code = "MEDIA_INVENTORY_ROW_APPLICABILITY_TAXONOMY_REQUIRED"

            if candidate.get("semantic_identity_candidate_available"):
                candidate_count += 1
            if candidate.get("identity_epistemic_status") == "inferred":
                inferred_identity_count += 1
            elif candidate.get("identity_epistemic_status") == "candidate":
                low_candidate_identity_count += 1
            if technical_observed:
                technical_observed_count += 1
            if technical_observed and not identity_observed:
                technical_only_count += 1
            if anatomy.get("extension_container_mismatch"):
                anatomy_mismatch_count += 1
                container_mismatch_identity_count += 1
            anatomy_counts[str(anatomy.get("observed_signature_family") or "unknown")] += 1
            row_class_counts[row_class] += 1

            identity_resolution = self._identity_resolution(
                row_class=row_class,
                observed_identity=observed_identity,
                candidate=candidate,
                anatomy=anatomy,
                technical_observed=technical_observed,
            )
            identity_status = str(identity_resolution.get("resolved_identity_source_status") or "unknown")
            if identity_status == "candidate":
                low_candidate_identity_count += 0
            elif identity_status == "unknown":
                unknown_identity_count += 1
            elif identity_status == "not_applicable":
                not_applicable_identity_count += 1
            elif identity_status == "unsupported":
                unsupported_identity_count += 1
            elif identity_status == "read_error":
                read_error_identity_count += 1
            elif identity_status == "container_mismatch":
                container_mismatch_identity_count += 0
            identity_status_counts[identity_status] += 1
            relationship_candidate = bool(relationship and relationship.get("likely_audio_entity_id"))
            scores = self.confidence_scoring.score_row(
                row_class=row_class,
                technical_observed=technical_observed,
                identity_status=identity_status,
                identity_confidence=float(identity_resolution.get("resolved_identity_confidence") or 0.0),
                container_confidence=float(anatomy.get("container_confidence") or 0.0),
                extension_container_mismatch=bool(anatomy.get("extension_container_mismatch")),
                relationship_candidate=relationship_candidate,
                has_entity_binding=bool(entity.get("entity_id") and entity.get("evidence_refs")),
            )
            catalog_status_counts[str(scores.get("catalog_item_status") or "cataloged_unknown_identity")] += 1
            for score_key in (
                "technical_score",
                "identity_observed_score",
                "identity_inferred_score",
                "identity_candidate_score",
                "container_score",
                "relationship_score",
                "evidence_binding_score",
                "row_applicability_score",
                "overall_catalog_confidence",
                "truth_claim_confidence",
                "planning_confidence",
            ):
                score_sums[score_key] += float(scores.get(score_key) or 0.0)
            use_safety = self._row_use_safety(
                row_class=row_class,
                identity_status=identity_status,
                scores=scores,
                reason_code=reason_code,
            )
            if use_safety["safe_for_catalog"] is True:
                safe_for_catalog_count += 1
            if use_safety["safe_for_planning"] in {True, "true_with_limitations"}:
                safe_for_planning_count += 1
            if use_safety["safe_for_truth_claim"] is True:
                safe_for_truth_claim_count += 1

            limitations = ["candidate_identity_not_truth"] if candidate.get("semantic_identity_candidate_available") else []
            if relationship:
                limitations.append("lyrics_sidecar_relationship_not_identity_truth")
            if anatomy.get("extension_container_mismatch"):
                limitations.append("container_signature_routing_hint_only")

            fields = {
                "entity_id": entity_id,
                "source_root_role": self._attribute_value(entity, "source_root_role") or entity.get("source_root_role"),
                "relative_path": self._relative_path(entity),
                "filename": self._filename(entity),
                "declared_extension": extension,
                "row_class": row_class,
                "primary_media_identity_required": extension in PRIMARY_MEDIA_EXTENSIONS,
                "semantic_identity_observed": identity_observed,
                "semantic_identity_candidate_available": bool(candidate.get("semantic_identity_candidate_available")),
                "candidate_identity_source": candidate.get("candidate_identity_source"),
                "candidate_identity_confidence": candidate.get("candidate_identity_confidence"),
                "candidate_title": candidate.get("candidate_title"),
                "candidate_artist": candidate.get("candidate_artist"),
                "candidate_album": candidate.get("candidate_album"),
                "candidate_source": candidate.get("candidate_source"),
                "candidate_method": candidate.get("candidate_method"),
                "candidate_reason": candidate.get("candidate_reason"),
                "candidate_risk_flags": ";".join(candidate.get("candidate_risk_flags") or []),
                "candidate_truth_status": "candidate_only_not_truth",
                "promoted_to_semantic_truth": False,
                "required_for_user_review": bool(candidate.get("semantic_identity_candidate_available")),
                **identity_resolution,
                **scores,
                **use_safety,
                "row_sufficiency_status": sufficiency_status,
                "row_sufficiency_reason_code": reason_code,
                "limitations": ";".join(limitations),
                "relationship_candidate_refs": self._relationship_ref(relationship),
                "sidecar_likely_audio_entity_id": relationship.get("likely_audio_entity_id") if relationship else None,
                "sidecar_match_method": relationship.get("match_method") if relationship else None,
                "sidecar_match_score": relationship.get("match_score") if relationship else None,
                "sidecar_relationship_status": relationship.get("relationship_status") if relationship else None,
                "sidecar_relationship_truth_status": relationship.get("relationship_truth_status") if relationship else None,
                "sidecar_relationship_risk_flags": ";".join(relationship.get("risk_flags") or [])
                if relationship
                else None,
                **anatomy,
            }
            rows_by_entity[entity_id] = fields

        total = len(rows_by_entity)
        primary_count = sum(row_class_counts[name] for name in (
            "primary_media_with_governed_identity",
            "primary_media_without_identity_tags",
            "primary_media_backend_no_valid_evidence",
        ))
        governed_identity_count = row_class_counts["primary_media_with_governed_identity"]
        lyrics_count = row_class_counts["lyrics_sidecar_candidate"]
        artwork_count = row_class_counts["artwork_candidate"]
        summary = {
            "all_rows_count": total,
            "primary_media_row_count": primary_count,
            "lyrics_sidecar_row_count": lyrics_count,
            "artwork_row_count": artwork_count,
            "primary_media_with_governed_identity_count": governed_identity_count,
            "primary_media_without_identity_tags_count": row_class_counts["primary_media_without_identity_tags"],
            "primary_media_backend_no_valid_evidence_count": row_class_counts["primary_media_backend_no_valid_evidence"],
            "primary_media_identity_ratio": self._ratio(governed_identity_count, primary_count),
            "all_rows_stable_entity_identity_ratio": self._ratio(total, total),
            "sidecar_relationship_candidate_count": sidecar_relationship_count,
            "artwork_candidate_count": artwork_count,
            "candidate_identity_available_count": candidate_count,
            "candidate_identity_not_truth_count": candidate_count,
            "inferred_identity_available_count": inferred_identity_count,
            "rows_observed_identity": identity_status_counts["observed"],
            "rows_inferred_identity": identity_status_counts["inferred"],
            "rows_candidate_identity": identity_status_counts["candidate"],
            "rows_unknown_identity": unknown_identity_count,
            "rows_not_applicable_identity": not_applicable_identity_count,
            "rows_unsupported_identity": unsupported_identity_count,
            "rows_read_error_identity": read_error_identity_count,
            "rows_container_mismatch": container_mismatch_identity_count,
            "identity_status_counts": dict(identity_status_counts),
            "catalog_item_status_counts": dict(catalog_status_counts),
            "rows_safe_for_catalog": safe_for_catalog_count,
            "rows_safe_for_planning": safe_for_planning_count,
            "rows_safe_for_truth_claim": safe_for_truth_claim_count,
            "technical_metadata_observed_count": technical_observed_count,
            "technical_metadata_only_count": technical_only_count,
            "file_anatomy_observed_count": total,
            "file_anatomy_extension_container_mismatch_count": anatomy_mismatch_count,
            "backend_no_valid_evidence_count": backend_no_valid_evidence_count,
            "row_class_counts": dict(row_class_counts),
            "file_anatomy_signature_family_counts": dict(anatomy_counts),
            "truth_policy": {
                "filename_identity_truth": False,
                "lyrics_sidecar_identity_truth": False,
                "container_signature_identity_truth": False,
                "inferred_identity_truth_status": "inferred_not_observed",
                "candidate_identity_truth_status": "candidate_only_not_truth",
            },
            "inventory_confidence": {
                "inventory_row_count": total,
                "primary_media_count": primary_count,
                "sidecar_count": lyrics_count,
                "artwork_count": artwork_count,
                "technical_coverage_score": self._average_score(score_sums, "technical_score", total),
                "observed_identity_coverage_score": self._ratio(identity_status_counts["observed"], primary_count),
                "inferred_identity_coverage_score": self._ratio(identity_status_counts["inferred"], primary_count),
                "candidate_identity_coverage_score": self._ratio(identity_status_counts["candidate"], primary_count),
                "unknown_identity_ratio": self._ratio(identity_status_counts["unknown"], primary_count),
                "container_confidence_score": self._average_score(score_sums, "container_score", total),
                "relationship_confidence_score": self._average_score(score_sums, "relationship_score", total),
                "evidence_binding_score": self._average_score(score_sums, "evidence_binding_score", total),
                "overall_catalog_confidence": self._average_score(score_sums, "overall_catalog_confidence", total),
                "truth_claim_confidence": self._average_score(score_sums, "truth_claim_confidence", total),
                "planning_confidence": self._average_score(score_sums, "planning_confidence", total),
                "safe_for_truth_claim": safe_for_truth_claim_count == total and total > 0,
                "safe_for_catalog": safe_for_catalog_count == total and total > 0,
                "safe_for_planning": "true_with_limitations" if safe_for_planning_count == total and total > 0 else False,
                "safe_for_downstream_static_analysis": "true_with_limitations"
                if safe_for_catalog_count == total and total > 0
                else False,
                "safe_for_destructive_action": False,
                "safe_for_user_report": "true_with_limitations" if safe_for_catalog_count == total and total > 0 else False,
            },
        }
        return {
            "rows_by_entity": rows_by_entity,
            "summary": summary,
        }

    def _media_observations_by_entity(self, perception_payload: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
        rows = perception_payload.get("attribute_observations") if isinstance(perception_payload.get("attribute_observations"), list) else []
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in rows:
            if not isinstance(item, dict):
                continue
            if str(item.get("capability_id") or "") != "media_metadata_reader":
                continue
            grouped[str(item.get("entity_id") or "")].append(item)
        return grouped

    def _has_identity_evidence(self, entity_id: str, bindings: dict[str, dict[str, list[dict[str, Any]]]]) -> bool:
        return bool(self._observed_identity_values(entity_id, bindings))

    def _observed_identity_values(
        self,
        entity_id: str,
        bindings: dict[str, dict[str, list[dict[str, Any]]]],
    ) -> dict[str, dict[str, Any]]:
        claims = bindings.get(entity_id) if isinstance(bindings, dict) else {}
        if not isinstance(claims, dict):
            return {}
        values: dict[str, dict[str, Any]] = {}
        for key in IDENTITY_KEYS:
            for item in claims.get(key) or []:
                if isinstance(item, dict) and item.get("value") not in (None, "") and item.get("evidence_refs"):
                    values[key] = {
                        "value": item.get("value"),
                        "evidence_refs": [str(ref) for ref in item.get("evidence_refs") or [] if ref],
                        "provenance_refs": [str(ref) for ref in item.get("provenance_refs") or [] if ref],
                        "source": item.get("capability_id") or item.get("observer_id") or "governed_evidence",
                        "source_method": item.get("backend_id") or "governed_backend",
                    }
                    break
        return values

    def _identity_resolution(
        self,
        *,
        row_class: str,
        observed_identity: dict[str, dict[str, Any]],
        candidate: dict[str, Any],
        anatomy: dict[str, Any],
        technical_observed: bool,
    ) -> dict[str, Any]:
        if row_class in {"lyrics_sidecar_candidate", "artwork_candidate", "non_primary_corpus_member"}:
            status = "not_applicable"
        elif anatomy.get("file_anatomy_status") == "read_error":
            status = "read_error"
        elif anatomy.get("extension_container_mismatch") and not technical_observed and not observed_identity:
            status = "container_mismatch"
        elif observed_identity:
            status = "observed"
        elif candidate.get("inferred_identity_available"):
            status = "inferred"
        elif candidate.get("semantic_identity_candidate_available"):
            status = "candidate"
        elif row_class == "primary_media_backend_no_valid_evidence":
            status = "unsupported"
        else:
            status = "unknown"

        observed_title = (observed_identity.get("track_title") or {}).get("value")
        observed_artist = (observed_identity.get("artist") or {}).get("value")
        observed_album = (observed_identity.get("album") or {}).get("value")
        observed_album_artist = (observed_identity.get("album_artist") or {}).get("value")
        inferred_title = candidate.get("inferred_title")
        inferred_artist = candidate.get("inferred_artist")
        inferred_album = candidate.get("inferred_album")
        inferred_album_artist = candidate.get("inferred_album_artist")
        candidate_title = candidate.get("candidate_title")
        candidate_artist = candidate.get("candidate_artist")
        candidate_album = candidate.get("candidate_album")
        candidate_album_artist = candidate.get("candidate_album_artist")
        confidence = (
            0.96
            if status == "observed"
            else float(candidate.get("inferred_identity_confidence") or 0.0)
            if status == "inferred"
            else float(candidate.get("candidate_identity_confidence") or 0.0)
            if status == "candidate"
            else 0.0
        )
        resolved_title = (
            observed_title
            if status == "observed"
            else inferred_title
            if status == "inferred"
            else candidate_title
            if status == "candidate"
            else None
        )
        resolved_artist = (
            observed_artist
            if status == "observed"
            else inferred_artist
            if status == "inferred"
            else candidate_artist
            if status == "candidate"
            else None
        )
        resolved_album = (
            observed_album
            if status == "observed"
            else inferred_album
            if status == "inferred"
            else candidate_album
            if status == "candidate"
            else None
        )
        limitations = self._identity_limitations(status=status, candidate=candidate, anatomy=anatomy)
        field_status = self._field_statuses(
            status=status,
            observed_identity=observed_identity,
            candidate=candidate,
            row_class=row_class,
            anatomy=anatomy,
        )
        field_models = {
            key: build_catalog_field(
                field_name=key,
                value=field_status[key]["value"],
                status=field_status[key]["status"],
                source=field_status[key]["source"],
                source_method=field_status[key]["source_method"],
                evidence_refs=field_status[key].get("evidence_refs") or [],
                confidence=float(field_status[key].get("confidence") or 0.0),
                limitations=limitations,
                risk_flags=list(candidate.get("candidate_risk_flags") or []),
                promoted_to_truth=False,
                safe_for_truth_claim=field_status[key]["status"] == "observed",
            )
            for key in ("track_title", "artist", "album", "album_artist")
        }
        return {
            "observed_track_title": observed_title,
            "observed_artist": observed_artist,
            "observed_album": observed_album,
            "observed_album_artist": observed_album_artist,
            "inferred_track_title": inferred_title,
            "inferred_artist": inferred_artist,
            "inferred_album": inferred_album,
            "inferred_album_artist": inferred_album_artist,
            "candidate_track_title": candidate_title,
            "candidate_artist": candidate_artist,
            "candidate_album": candidate_album,
            "candidate_album_artist": candidate_album_artist,
            "resolved_display_title": resolved_title,
            "resolved_display_artist": resolved_artist,
            "resolved_display_album": resolved_album,
            "resolved_identity_source_status": status,
            "resolved_identity_confidence": round(max(0.0, min(1.0, confidence)), 4),
            "resolved_identity_limitations": ";".join(limitations),
            "track_title_status": field_status["track_title"]["status"],
            "artist_status": field_status["artist"]["status"],
            "album_status": field_status["album"]["status"],
            "album_artist_status": field_status["album_artist"]["status"],
            "track_title_confidence": field_status["track_title"]["confidence"],
            "artist_confidence": field_status["artist"]["confidence"],
            "album_confidence": field_status["album"]["confidence"],
            "album_artist_confidence": field_status["album_artist"]["confidence"],
            "catalog_field_statuses": field_models,
            "filename_identity_promoted_to_truth": False,
            "container_identity_promoted_to_truth": False,
            "lyrics_identity_promoted_to_truth": False,
        }

    def _field_statuses(
        self,
        *,
        status: str,
        observed_identity: dict[str, dict[str, Any]],
        candidate: dict[str, Any],
        row_class: str,
        anatomy: dict[str, Any],
    ) -> dict[str, dict[str, Any]]:
        fields: dict[str, dict[str, Any]] = {}
        non_primary = row_class in {"lyrics_sidecar_candidate", "artwork_candidate", "non_primary_corpus_member"}
        for key in ("track_title", "artist", "album", "album_artist"):
            observed = observed_identity.get(key) or {}
            if observed:
                fields[key] = {
                    "value": observed.get("value"),
                    "status": "observed",
                    "source": observed.get("source") or "governed_evidence",
                    "source_method": observed.get("source_method") or "governed_backend",
                    "evidence_refs": observed.get("evidence_refs") or [],
                    "confidence": 0.96,
                }
                continue
            inferred_key = {
                "track_title": "inferred_title",
                "artist": "inferred_artist",
                "album": "inferred_album",
                "album_artist": "inferred_album_artist",
            }[key]
            candidate_key = {
                "track_title": "candidate_title",
                "artist": "candidate_artist",
                "album": "candidate_album",
                "album_artist": "candidate_album_artist",
            }[key]
            if non_primary:
                field_status = "not_applicable"
            elif anatomy.get("file_anatomy_status") == "read_error":
                field_status = "read_error"
            elif anatomy.get("extension_container_mismatch"):
                field_status = "container_mismatch"
            elif candidate.get("inferred_identity_available") and candidate.get(inferred_key) not in (None, ""):
                field_status = "inferred"
            elif candidate.get(candidate_key) not in (None, ""):
                field_status = "candidate"
            elif row_class == "primary_media_backend_no_valid_evidence":
                field_status = "unsupported"
            else:
                field_status = "unknown"
            value = (
                candidate.get(inferred_key)
                if field_status == "inferred"
                else candidate.get(candidate_key)
                if field_status == "candidate"
                else None
            )
            confidence = (
                float(candidate.get("inferred_identity_confidence") or 0.0)
                if field_status == "inferred"
                else float(candidate.get("candidate_identity_confidence") or 0.0)
                if field_status == "candidate"
                else 0.0
            )
            fields[key] = {
                "value": value,
                "status": field_status,
                "source": "filename" if field_status in {"inferred", "candidate"} else "row_applicability_policy",
                "source_method": str(candidate.get("candidate_method") or "none"),
                "evidence_refs": [],
                "confidence": round(max(0.0, min(1.0, confidence)), 4),
            }
        return fields

    def _identity_limitations(self, *, status: str, candidate: dict[str, Any], anatomy: dict[str, Any]) -> list[str]:
        limitations: list[str] = []
        if status == "observed":
            limitations.append("observed_identity_bound_to_governed_evidence")
        elif status == "inferred":
            limitations.append("inferred_identity_not_observed_truth")
        elif status == "candidate":
            limitations.append("candidate_identity_requires_review")
        elif status == "not_applicable":
            limitations.append("identity_not_applicable_to_row_class")
        elif status == "container_mismatch":
            limitations.append("container_mismatch_prevents_strong_identity_claim")
        elif status == "unsupported":
            limitations.append("current_backend_did_not_produce_valid_identity_evidence")
        elif status == "read_error":
            limitations.append("file_read_error_prevents_identity_resolution")
        else:
            limitations.append("identity_unknown_not_false")
        limitations.extend(str(flag) for flag in candidate.get("candidate_risk_flags") or [])
        if anatomy.get("extension_container_mismatch"):
            limitations.append("container_signature_routing_hint_only")
        return list(dict.fromkeys(limitations))

    def _row_use_safety(
        self,
        *,
        row_class: str,
        identity_status: str,
        scores: dict[str, Any],
        reason_code: str | None,
    ) -> dict[str, Any]:
        row_known = bool(row_class and row_class != "unknown_or_unclassified")
        truth_safe = identity_status == "observed" and not reason_code
        planning_safe: bool | str = True if truth_safe else "true_with_limitations" if row_known else False
        catalog_safe: bool | str = True if row_known else False
        return {
            "safe_for_truth_claim": truth_safe,
            "safe_for_catalog": catalog_safe,
            "safe_for_planning": planning_safe,
            "safe_for_downstream_static_analysis": "true_with_limitations" if row_known else False,
            "safe_for_destructive_action": False,
            "safe_for_user_report": True if truth_safe else "true_with_limitations" if row_known else False,
            "use_safety_reason_code": None if truth_safe else "CATALOG_SAFE_FOR_PLANNING_WITH_LIMITATIONS" if row_known else "CATALOG_ROW_CLASS_UNKNOWN",
            "use_safety_limitations": (
                "not_safe_for_full_truth_claim"
                if not truth_safe
                else "observed_identity_supports_truth_claim_for_row"
            ),
            "safe_to_use": truth_safe,
            "legacy_safe_to_use": truth_safe,
            "artifact_use_safety_basis": f"identity_status={identity_status};catalog_item_status={scores.get('catalog_item_status')}",
        }

    def _has_technical_metadata(self, observations: list[dict[str, Any]]) -> bool:
        for item in observations:
            if item.get("observation_state") != "observed":
                continue
            key = str(item.get("canonical_key") or item.get("attribute_name") or "")
            if key in TECHNICAL_MEDIA_KEYS and item.get("observed_value") not in (None, ""):
                return True
        return False

    def _audio_index(self, audio_entities: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        index: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for entity in audio_entities:
            filename = self._filename(entity)
            stem = self._normalized_stem(Path(filename).stem if filename else "")
            if stem:
                index[stem].append(entity)
        return index

    def _lyrics_relationship(self, entity: dict[str, Any], *, audio_by_stem: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        filename = self._filename(entity)
        stem = self._normalized_stem(Path(filename).stem if filename else "")
        matches = audio_by_stem.get(stem) or []
        if not matches:
            return {
                "relationship_status": "unmatched",
                "relationship_truth_status": "candidate_only_not_truth",
                "match_method": "basename",
                "match_score": 0.0,
                "risk_flags": ["LYRICS_SIDECAR_UNMATCHED", "LYRICS_SIDECAR_NOT_IDENTITY_TRUTH"],
                "full_lyrics_included": False,
            }
        match = matches[0]
        relationship_status = "relationship_inferred" if len(matches) == 1 else "relationship_candidate"
        return {
            "likely_audio_entity_id": str(match.get("entity_id") or ""),
            "likely_audio_relative_path": self._relative_path(match),
            "relationship_status": relationship_status,
            "relationship_truth_status": "candidate_only_not_truth",
            "match_method": "basename",
            "match_score": 1.0 if len(matches) == 1 else 0.7,
            "risk_flags": ["LYRICS_SIDECAR_RELATIONSHIP_CANDIDATE", "LYRICS_SIDECAR_NOT_IDENTITY_TRUTH"],
            "full_lyrics_included": False,
        }

    def _relationship_ref(self, relationship: dict[str, Any] | None) -> str:
        if not relationship:
            return ""
        audio_id = str(relationship.get("likely_audio_entity_id") or "")
        return f"candidate_audio:{audio_id}" if audio_id else ""

    def _extension(self, entity: dict[str, Any]) -> str:
        extension = str(entity.get("extension") or self._attribute_value(entity, "extension") or "")
        if not extension:
            filename = self._filename(entity)
            extension = Path(filename).suffix.lstrip(".") if filename else ""
        return extension.casefold().lstrip(".")

    def _filename(self, entity: dict[str, Any]) -> str:
        name = str(entity.get("filename") or entity.get("name") or self._attribute_value(entity, "name") or "")
        if name:
            return name
        relative_path = self._relative_path(entity)
        return Path(relative_path).name if relative_path else ""

    def _relative_path(self, entity: dict[str, Any]) -> str:
        return str(entity.get("relative_path") or self._attribute_value(entity, "relative_path") or "")

    def _attribute_value(self, entity: dict[str, Any], key: str) -> Any:
        for container_name in ("observed_attributes", "inferred_attributes"):
            container = entity.get(container_name)
            if not isinstance(container, dict):
                continue
            raw = container.get(key)
            if isinstance(raw, dict) and "value" in raw:
                return raw.get("value")
        return None

    def _normalized_stem(self, value: str) -> str:
        value = re.sub(r"\s+-\s+\d+$", "", value or "")
        value = re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
        return re.sub(r"\s+", " ", value)

    def _ratio(self, numerator: int, denominator: int) -> float:
        return round(numerator / max(1, denominator), 4) if denominator else 0.0

    def _average_score(self, score_sums: Counter[str], key: str, denominator: int) -> float:
        return round(float(score_sums.get(key) or 0.0) / max(1, denominator), 4) if denominator else 0.0
