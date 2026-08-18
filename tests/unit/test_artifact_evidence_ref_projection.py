from aipinho.schemas.artifacts.artifact_interaction_contracts import ArtifactRecord
from aipinho.services.artifacts.universal_artifact_registry_service import UniversalArtifactRegistryService


class ExplodingLegacyRegistry:
    def list(self):
        raise AssertionError("legacy registry scan should not run for task_run lookup without index")


def test_artifact_index_projects_lightweight_row_evidence_refs() -> None:
    record = ArtifactRecord(
        artifact_id="artifact_inventory_projection",
        logical_path="reports/corpus/inventory.csv",
        filename="inventory.csv",
        content_type="text/csv",
        size_bytes=42,
        sha256="0" * 64,
        storage_path="data/artifacts/universal/inventory.csv",
        task_id="task_1",
        task_run_id="task_run_1",
        owner_task_id="task_run_1",
        producer_step="readonly_analysis_artifact_runtime",
        evidence_refs=["task_run:task_run_1", "file:one"],
        metadata={
            "selected_rows": 1,
            "bound_rows": 1,
            "evidence_ref_count": 1,
            "evidence_refs_sample": ["file:one"],
            "row_evidence_coverage": {"status": "satisfied", "evidence_ref_count": 1},
            "row_validation_summary": {"status": "satisfied", "row_count": 1},
            "rendered_columns": ["entity_id", "evidence_ref"],
            "missing_columns": [],
        },
    )
    registry = UniversalArtifactRegistryService()

    row = registry._light_index_record(record)
    public = registry._public_index_record(row)

    assert public["artifact_id"] == "artifact_inventory_projection"
    assert public["evidence_refs"] == ["task_run:task_run_1", "file:one"]
    assert public["evidence_refs_sample"] == ["file:one"]
    assert public["row_evidence_coverage"]["evidence_ref_count"] == 1
    assert public["missing_columns"] == []


def test_task_run_lookup_without_artifact_index_does_not_scan_legacy_registry(tmp_path) -> None:
    registry = UniversalArtifactRegistryService(
        registry=ExplodingLegacyRegistry(),
        store_root=tmp_path / "store",
        index_root=tmp_path / "index",
    )

    rows = registry.by_task("task_run_without_artifacts", limit=20)

    assert rows == []
