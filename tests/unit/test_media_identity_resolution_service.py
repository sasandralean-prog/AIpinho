from __future__ import annotations

from aipinho.services.artifacts.media_candidate_identity_policy import MediaCandidateIdentityPolicy
from aipinho.services.artifacts.media_identity_resolution_service import MediaIdentityResolutionService


def test_observed_identity_beats_inferred_filename_identity() -> None:
    candidate = MediaCandidateIdentityPolicy().evaluate({"filename": "Other - Guess.m4a"})
    resolved = MediaIdentityResolutionService().resolve(
        row_class="primary_media_with_governed_identity",
        observed_identity={"track_title": {"value": "Observed", "evidence_refs": ["e1"]}},
        candidate_identity=candidate,
        anatomy={},
        technical_observed=True,
    )

    assert resolved["status"] == "observed"
    assert resolved["safe_for_truth_claim"] is True


def test_filename_artist_title_pattern_is_inferred_not_observed() -> None:
    candidate = MediaCandidateIdentityPolicy().evaluate({"filename": "A Day To Remember - All I Want.m4a"})
    resolved = MediaIdentityResolutionService().resolve(
        row_class="primary_media_without_identity_tags",
        observed_identity={},
        candidate_identity=candidate,
        anatomy={},
        technical_observed=True,
    )

    assert candidate["inferred_identity_available"] is True
    assert resolved["status"] == "inferred"
    assert resolved["safe_for_truth_claim"] is False
    assert resolved["promoted_to_observed_truth"] is False


def test_duplicate_suffix_stays_candidate_not_inferred_artist_title() -> None:
    candidate = MediaCandidateIdentityPolicy().evaluate({"filename": "505 - 2.m4a"})
    resolved = MediaIdentityResolutionService().resolve(
        row_class="primary_media_without_identity_tags",
        observed_identity={},
        candidate_identity=candidate,
        anatomy={},
        technical_observed=True,
    )

    assert candidate["inferred_identity_available"] is False
    assert candidate["candidate_artist"] is None
    assert resolved["status"] == "candidate"
