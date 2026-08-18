from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService


def test_artifact_projection_keeps_media_inventory_summaries_lightweight() -> None:
    service = UniversalTaskSessionService()
    row = service._light_artifact_row(
        {
            "logical_path": "reports/example/inventory.csv",
            "status": "partial",
            "safe_to_use": False,
            "schema_coverage": {
                "status": "partial",
                "canonical_schema": ["entity_id", "relative_path", "codec"],
                "semantic_entity_selection": {"entities": [{"entity_id": f"entity_{i}"} for i in range(20)]},
                "metadata_coverage_summary": {
                    "status": "satisfied",
                    "files_expected": 2,
                    "files_succeeded": 2,
                },
                "inventory_sufficiency_summary": {
                    "status": "blocked",
                    "reason_code": "MEDIA_INVENTORY_COVERAGE_INSUFFICIENT",
                    "safe_to_use": False,
                    "use_safety": {"phase1_discovery": False, "full_truth_claim": False},
                },
            },
        }
    )

    assert row["schema_coverage"]["metadata_coverage_summary"]["files_succeeded"] == 2
    assert row["schema_coverage"]["inventory_sufficiency_summary"]["safe_to_use"] is False
    assert "semantic_entity_selection" not in row["schema_coverage"]
    assert "canonical_schema" not in row["schema_coverage"]
