from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


def test_media_metadata_capability_remains_not_configured_without_media_provenance() -> None:
    service = UniversalTaskSessionService()

    summary = service._media_metadata_capability_summary([], evidence_by_attribute={"entity_id": 2})

    assert summary["status"] == "not_configured"
    assert summary["capability_id"] == "media_metadata_reader"


def test_relationship_not_available_has_causal_reason_code() -> None:
    service = UniversalTaskSessionService()

    summary = service._relationship_cognition_summary([], [], [])

    assert summary["status"] == "not_available"
    assert summary["truth_eligible"] is False
    assert summary["reason_codes"] == ["RELATIONSHIP_OBSERVATION_NOT_BOUND"]
