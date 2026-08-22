from __future__ import annotations

from aipinho.services.artifacts.media_candidate_identity_policy import MediaCandidateIdentityPolicy


def _entity(name: str) -> dict:
    return {"entity_id": "entity_1", "name": name, "extension": name.rsplit(".", 1)[-1]}


def test_artist_title_filename_pattern_is_candidate_only_not_truth() -> None:
    result = MediaCandidateIdentityPolicy().evaluate(_entity("A Day To Remember - All I Want.m4a"))

    assert result["candidate_artist"] == "A Day To Remember"
    assert result["candidate_title"] == "All I Want"
    assert result["candidate_method"] == "artist_title_separator_candidate"
    assert result["candidate_truth_status"] == "candidate_only_not_truth"
    assert result["promoted_to_semantic_truth"] is False


def test_duplicate_suffix_pattern_is_flagged_not_confident_artist_title() -> None:
    result = MediaCandidateIdentityPolicy().evaluate(_entity("505 - 2.m4a"))

    assert result["candidate_artist"] is None
    assert result["candidate_title"] == "505 - 2"
    assert "duplicate_suffix_candidate" in result["candidate_risk_flags"]
    assert "numeric_title_candidate" in result["candidate_risk_flags"]
    assert "low_confidence_candidate" in result["candidate_risk_flags"]
    assert result["candidate_truth_status"] == "candidate_only_not_truth"
    assert result["promoted_to_semantic_truth"] is False
