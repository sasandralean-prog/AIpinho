from __future__ import annotations

from typing import Any


class MediaIdentityResolutionService:
    """Resolves media display identity as observed, inferred, candidate, or unknown."""

    def resolve(
        self,
        *,
        row_class: str,
        observed_identity: dict[str, dict[str, Any]],
        candidate_identity: dict[str, Any],
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
        elif candidate_identity.get("inferred_identity_available"):
            status = "inferred"
        elif candidate_identity.get("semantic_identity_candidate_available"):
            status = "candidate"
        elif row_class == "primary_media_backend_no_valid_evidence":
            status = "unsupported"
        else:
            status = "unknown"
        return {
            "status": status,
            "safe_for_truth_claim": status == "observed",
            "promoted_to_observed_truth": False,
        }
