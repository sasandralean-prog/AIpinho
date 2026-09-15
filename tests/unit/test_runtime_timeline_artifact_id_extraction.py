from __future__ import annotations

from types import SimpleNamespace

from aipinho.services.runtime.runtime_timeline_service import RuntimeTimelineService


def test_artifact_id_extraction_ignores_structured_observed_attribute() -> None:
    result = SimpleNamespace(
        outputs={
            "artifact_records": [{"artifact_id": "artifact_12345678"}],
            "observed_entity_graph": {
                "observed_attributes": {
                    "artifact_id": {
                        "name": "artifact_id",
                        "value": "artifact_deadbeef",
                        "status": "observed",
                    }
                }
            },
        }
    )

    ids = RuntimeTimelineService()._artifact_ids_from_result(result)

    assert ids == ["artifact_12345678"]
    assert all(not item.startswith("{") for item in ids)
