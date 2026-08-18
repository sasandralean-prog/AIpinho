from __future__ import annotations

import shutil

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_interaction_contracts import UniversalArtifactCreateRequest
from aipinho.services.artifacts.artifact_interaction_core import ArtifactRegistryRepository
from aipinho.services.artifacts.universal_artifact_registry_service import UniversalArtifactRegistryService


def test_corrupt_legacy_artifact_registry_does_not_block_new_artifact_creation(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("aipinho.services.artifacts.artifact_interaction_core._LEGACY_REGISTRY_MAX_BYTES", 16)
    root = PATHS.project_root / ".tmp_pytest_artifact_registry" / tmp_path.name
    shutil.rmtree(root, ignore_errors=True)
    legacy_path = root / "manifests" / "artifact_registry.json"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text("[" + "x" * 128, encoding="utf-8")
    registry = ArtifactRegistryRepository(path=legacy_path)
    service = UniversalArtifactRegistryService(
        registry=registry,
        store_root=root / "artifacts",
        index_root=root / "artifact_index",
    )

    try:
        record = service.create(
            UniversalArtifactCreateRequest(
                source_agent="aipinho",
                filename="discovery.md",
                logical_path="reports/runtime/discovery.md",
                artifact_type="readonly_analysis_report",
                producer_step="readonly_analysis_artifact_runtime",
                event_id="event_artifact_started",
                task_id="task_generic",
                task_run_id="task_run_generic",
                owner_task_id="task_run_generic",
                content_type="text/markdown",
                content="# Discovery\n",
                status="ready",
                validation_status="validated",
                metadata={"semantic_contract_status": "satisfied"},
            )
        )

        assert record.status == "ready"
        assert (legacy_path.parent / "by_artifact" / f"{record.artifact_id}.json").exists()
        assert (legacy_path.parent / "artifact_registry_index.json").exists()
        assert (legacy_path.parent / "artifact_registry_diagnostic.json").exists()
        assert service.get(record.artifact_id)["artifact_id"] == record.artifact_id
        assert service.by_task("task_run_generic")[0]["artifact_id"] == record.artifact_id
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_sharded_artifact_registry_list_ignores_unreadable_legacy_projection(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("aipinho.services.artifacts.artifact_interaction_core._LEGACY_REGISTRY_MAX_BYTES", 16)
    root = PATHS.project_root / ".tmp_pytest_artifact_registry" / tmp_path.name
    shutil.rmtree(root, ignore_errors=True)
    legacy_path = root / "manifests" / "artifact_registry.json"
    legacy_path.parent.mkdir(parents=True)
    legacy_path.write_text("[" + "x" * 128, encoding="utf-8")
    registry = ArtifactRegistryRepository(path=legacy_path)
    service = UniversalArtifactRegistryService(
        registry=registry,
        store_root=root / "artifacts",
        index_root=root / "artifact_index",
    )
    try:
        record = service.create(
            UniversalArtifactCreateRequest(
                source_agent="aipinho",
                filename="inventory.csv",
                logical_path="reports/runtime/inventory.csv",
                artifact_type="readonly_analysis_report",
                producer_step="readonly_analysis_artifact_runtime",
                event_id="event_artifact_started",
                task_id="task_generic",
                task_run_id="task_run_generic",
                owner_task_id="task_run_generic",
                content_type="text/csv",
                content="entity_id,evidence_ref\nentity_1,evidence_1\n",
                status="partial",
                validation_status="partial",
                metadata={
                    "semantic_contract_status": "partial",
                    "safe_to_use": False,
                    "bound_rows": 1,
                    "evidence_ref_count": 1,
                },
            )
        )

        listed = registry.list()

        assert [item.artifact_id for item in listed] == [record.artifact_id]
        assert registry.get(record.artifact_id) is not None
    finally:
        shutil.rmtree(root, ignore_errors=True)
