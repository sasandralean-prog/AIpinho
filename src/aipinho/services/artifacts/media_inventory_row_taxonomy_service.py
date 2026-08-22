from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

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
    ) -> None:
        self.file_container_signatures = file_container_signatures or FileContainerSignatureService()
        self.candidate_identity_policy = candidate_identity_policy or MediaCandidateIdentityPolicy()

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

        for entity in selected_entities:
            entity_id = str(entity.get("entity_id") or "")
            if not entity_id:
                continue
            extension = self._extension(entity)
            identity_observed = self._has_identity_evidence(entity_id, claim_evidence_bindings)
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
            if technical_observed:
                technical_observed_count += 1
            if technical_observed and not identity_observed:
                technical_only_count += 1
            if anatomy.get("extension_container_mismatch"):
                anatomy_mismatch_count += 1
            anatomy_counts[str(anatomy.get("observed_signature_family") or "unknown")] += 1
            row_class_counts[row_class] += 1

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
                "candidate_identity_truth_status": "candidate_only_not_truth",
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
        claims = bindings.get(entity_id) if isinstance(bindings, dict) else {}
        if not isinstance(claims, dict):
            return False
        for key in IDENTITY_KEYS:
            for item in claims.get(key) or []:
                if isinstance(item, dict) and item.get("value") not in (None, "") and item.get("evidence_refs"):
                    return True
        return False

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
        return {
            "likely_audio_entity_id": str(match.get("entity_id") or ""),
            "likely_audio_relative_path": self._relative_path(match),
            "relationship_status": "candidate",
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
