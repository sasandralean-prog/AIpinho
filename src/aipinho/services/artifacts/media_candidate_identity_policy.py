from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class MediaCandidateIdentityPolicy:
    """Projects filename-derived media identity candidates without Truth promotion."""

    def evaluate(self, entity: dict[str, Any]) -> dict[str, Any]:
        filename = self._filename(entity)
        stem = Path(filename).stem if filename else ""
        if not stem:
            return {"semantic_identity_candidate_available": False, "candidate_risk_flags": ["candidate_not_truth"]}

        flags = ["candidate_not_truth"]
        title = stem
        artist = None
        method = "filename_stem"
        confidence = 0.35
        reason = "filename_stem_only"
        epistemic_status = "candidate"

        if re.search(r"\s-\s\d+$", stem):
            flags.extend(["duplicate_suffix_candidate", "numeric_title_candidate", "low_confidence_candidate"])
        elif " - " in stem:
            left, right = [part.strip() for part in stem.split(" - ", 1)]
            if left and right and not right.isdigit():
                artist = left
                title = right
                method = "artist_title_separator_candidate"
                confidence = 0.72
                reason = "artist_title_separator_inferred"
                epistemic_status = "inferred"
                flags.append("artist_title_separator_candidate")
            else:
                flags.extend(["duplicate_suffix_candidate", "numeric_title_candidate", "low_confidence_candidate"])
        else:
            flags.append("filename_stem_only")

        inferred = epistemic_status == "inferred"
        candidate = epistemic_status == "candidate"
        return {
            "semantic_identity_candidate_available": True,
            "inferred_identity_available": inferred,
            "identity_epistemic_status": epistemic_status,
            "identity_inference_rule_id": "artist_title_separator_rule" if inferred else None,
            "identity_inference_source": "filename" if inferred else None,
            "inferred_title": title if inferred else None,
            "inferred_artist": artist if inferred else None,
            "inferred_album": None,
            "inferred_album_artist": None,
            "inferred_identity_confidence": round(confidence, 2) if inferred else 0.0,
            "candidate_title": title,
            "candidate_artist": artist,
            "candidate_album": None,
            "candidate_album_artist": None,
            "candidate_track_title": title if candidate else None,
            "candidate_identity_epistemic_status": "candidate" if candidate else None,
            "candidate_source": "filename",
            "candidate_identity_source": "filename",
            "candidate_method": method,
            "candidate_identity_confidence": round(confidence, 2),
            "candidate_reason": reason,
            "candidate_risk_flags": list(dict.fromkeys(flags)),
            "candidate_truth_status": "candidate_only_not_truth",
            "promoted_to_semantic_truth": False,
            "safe_for_truth_claim": False,
        }

    def _filename(self, entity: dict[str, Any]) -> str:
        name = str(entity.get("filename") or entity.get("name") or self._attribute_value(entity, "name") or "")
        if name:
            return name
        relative_path = str(entity.get("relative_path") or self._attribute_value(entity, "relative_path") or "")
        return Path(relative_path).name if relative_path else ""

    def _attribute_value(self, entity: dict[str, Any], key: str) -> Any:
        for container_name in ("observed_attributes", "inferred_attributes"):
            container = entity.get(container_name)
            if not isinstance(container, dict):
                continue
            raw = container.get(key)
            if isinstance(raw, dict) and "value" in raw:
                return raw.get("value")
        return None
