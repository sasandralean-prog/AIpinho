from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

import pytest

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_runtime import ArtifactRuntimeCreateRequest
from aipinho.services.artifacts.artifact_interaction_core import ArtifactRegistryRepository
from aipinho.services.artifacts.artifact_runtime_service import ArtifactRuntimeService
from aipinho.services.artifacts.universal_artifact_registry_service import UniversalArtifactRegistryService


def _root() -> Path:
    root = PATHS.project_root / "data" / "tmp_artifact_runtime_tests" / uuid4().hex
    root.mkdir(parents=True, exist_ok=True)
    return root


def _runtime(root: Path) -> ArtifactRuntimeService:
    registry = ArtifactRegistryRepository(root / "artifact_registry.json")
    universal = UniversalArtifactRegistryService(registry=registry, store_root=root / "artifacts", index_root=root / "artifact_index")
    return ArtifactRuntimeService(registry=universal)


def _workspace(root: Path) -> Path:
    workspace = root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "src").mkdir()
    (workspace / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
    return workspace


def _hash_tree(path: Path) -> dict[str, str]:
    return {
        str(item.relative_to(path)): hashlib.sha256(item.read_bytes()).hexdigest()
        for item in sorted(path.rglob("*"))
        if item.is_file()
    }


def test_artifact_runtime_creates_artifact_without_workspace_mutation() -> None:
    root = _root()
    workspace = _workspace(root)
    before = _hash_tree(workspace)
    runtime = _runtime(root)

    artifact = runtime.create(
        ArtifactRuntimeCreateRequest(
            logical_path="reports/firetest5/phase1.md",
            content="# Phase 1\n\nEvidence.\n",
            content_type="text/markdown",
            artifact_type="analysis_report",
            producer_step="phase1_readonly_analysis",
            event_id="task_run_event_phase1",
            task_id="task_firetest5",
            task_run_id="task_run_firetest5",
            validation_status="validated",
        )
    )

    assert artifact.artifact_id.startswith("artifact_")
    assert artifact.logical_path == "reports/firetest5/phase1.md"
    assert artifact.task_id == "task_firetest5"
    assert artifact.task_run_id == "task_run_firetest5"
    assert artifact.producer_step == "phase1_readonly_analysis"
    assert artifact.event_id == "task_run_event_phase1"
    assert artifact.storage_ref
    assert artifact.local_path
    assert Path(artifact.local_path).exists()
    assert not str(Path(artifact.local_path).resolve()).startswith(str(workspace.resolve()))
    assert _hash_tree(workspace) == before


def test_artifact_registry_reads_utf8_bom_legacy_stub() -> None:
    root = _root()
    registry_path = root / "artifact_registry.json"
    registry_path.write_text("[]", encoding="utf-8-sig")

    registry = ArtifactRegistryRepository(registry_path)

    assert registry.list() == []


def test_artifact_runtime_treats_prompt_path_as_logical_path() -> None:
    root = _root()
    runtime = _runtime(root)

    artifact = runtime.create(
        ArtifactRuntimeCreateRequest(
            logical_path=r"reports\firetest5\test.md",
            content="logical path only\n",
            producer_step="readonly_report",
            task_id="task_logical",
            task_run_id="task_run_logical",
            event_id="task_run_event_logical",
            validation_status="validated",
        )
    )
    public = runtime.get(artifact.artifact_id)

    assert public is not None
    assert public["logical_path"] == "reports/firetest5/test.md"
    assert public["storage_ref"]
    assert public["storage_ref"] != public["logical_path"]
    assert Path(str(public["local_path"])).exists()


def test_artifact_runtime_validation_uses_storage_and_hash() -> None:
    root = _root()
    runtime = _runtime(root)

    artifact = runtime.create(
        ArtifactRuntimeCreateRequest(
            logical_path="reports/firetest5/validation.json",
            content='{"ok": true}\n',
            content_type="application/json",
            producer_step="validation_step",
            task_id="task_validation",
            task_run_id="task_run_validation",
            event_id="task_run_event_validation",
            validation_status="validated",
            evidence_refs=["task_run:task_run_validation"],
        )
    )
    validation = runtime.validate(artifact.artifact_id)

    assert validation.status == "passed"
    assert validation.validation_status == "validated"
    assert validation.logical_path == "reports/firetest5/validation.json"
    assert validation.storage_ref == artifact.storage_ref
    assert validation.safe_to_use_as_evidence is True
    assert validation.missing_reasons == []


def test_artifact_runtime_lookup_by_task_and_rejects_absolute_logical_path() -> None:
    root = _root()
    runtime = _runtime(root)

    created = runtime.create(
        ArtifactRuntimeCreateRequest(
            logical_path="reports/firetest5/index.md",
            content="index\n",
            producer_step="index_step",
            task_id="task_lookup",
            task_run_id="task_run_lookup",
            event_id="task_run_event_lookup",
            validation_status="validated",
        )
    )
    lookup = runtime.by_task("task_run_lookup", logical_path="reports/firetest5/index.md")

    assert lookup.status == "ok"
    assert lookup.count == 1
    assert lookup.artifacts[0]["artifact_id"] == created.artifact_id

    with pytest.raises(ValueError, match="artifact_logical_path_must_not_be_absolute"):
        runtime.create(
            ArtifactRuntimeCreateRequest(
                logical_path=r"C:\Users\rafae\Documents\project\reports\bad.md",
                content="bad\n",
                producer_step="bad_step",
                task_run_id="task_run_bad",
            )
        )


def test_artifact_runtime_lookup_uses_task_run_index_without_result_payload() -> None:
    root = _root()
    runtime = _runtime(root)

    created = runtime.create(
        ArtifactRuntimeCreateRequest(
            logical_path="reports/firetest5/music_inventory.csv",
            content="name,metadata\ntrack,{\"content_ref\":\"data/runtime/ref.json\"}\n",
            content_type="text/csv",
            producer_step="readonly_analysis_artifact_runtime",
            task_id="task_indexed",
            task_run_id="task_run_indexed",
            event_id="task_run_event_started",
            validation_status="validated",
        )
    )

    index_file = root / "artifact_index" / "by_task_run" / "task_run_indexed.json"
    assert index_file.exists()

    lookup = runtime.by_task("task_run_indexed")

    assert lookup.count == 1
    assert lookup.artifacts[0]["artifact_id"] == created.artifact_id
    assert lookup.artifacts[0]["logical_path"] == "reports/firetest5/music_inventory.csv"
    assert lookup.artifacts[0]["size_bytes"] == created.size_bytes
    assert lookup.artifacts[0]["storage_ref"]


def test_artifact_runtime_public_reads_use_index_without_global_registry_scan(monkeypatch) -> None:
    root = _root()
    runtime = _runtime(root)

    created = runtime.create(
        ArtifactRuntimeCreateRequest(
            logical_path="reports/firetest5/indexed.md",
            content="indexed\n",
            producer_step="readonly_analysis_artifact_runtime",
            task_id="task_indexed_fast",
            task_run_id="task_run_indexed_fast",
            event_id="task_run_event_indexed_fast",
            validation_status="validated",
        )
    )

    def fail_list():
        raise AssertionError("global_artifact_registry_scan_not_allowed_for_indexed_public_read")

    monkeypatch.setattr(runtime.registry.registry, "list", fail_list)

    public = runtime.get(created.artifact_id)
    revalidated = runtime.revalidate_public(created.artifact_id)
    lookup = runtime.by_task("task_run_indexed_fast")

    assert public is not None
    assert public["artifact_id"] == created.artifact_id
    assert revalidated is not None
    assert revalidated["status"] == "ready"
    assert lookup.count == 1
    assert lookup.artifacts[0]["artifact_id"] == created.artifact_id


def test_artifact_runtime_task_run_lookup_without_index_does_not_scan_tool_store(monkeypatch) -> None:
    root = _root()
    runtime = _runtime(root)

    def fail_tool_scan(*, include_all: bool = False):
        raise AssertionError("tool_store_global_scan_not_allowed_for_task_run_lookup")

    monkeypatch.setattr(runtime.registry.tool_store, "list_artifacts", fail_tool_scan)

    lookup = runtime.by_task("task_run_without_artifacts_yet")

    assert lookup.status == "ok"
    assert lookup.count == 0
    assert lookup.artifacts == []


def test_artifact_runtime_rejects_orphan_artifact_without_task_binding() -> None:
    root = _root()
    runtime = _runtime(root)

    with pytest.raises(ValueError, match="artifact_task_binding_required"):
        runtime.create(
            ArtifactRuntimeCreateRequest(
                logical_path="reports/orphan.md",
                content="orphan\n",
                producer_step="orphan_step",
            )
        )


def test_artifact_runtime_validation_blocks_missing_event_binding() -> None:
    root = _root()
    runtime = _runtime(root)

    artifact = runtime.create(
        ArtifactRuntimeCreateRequest(
            logical_path="reports/missing_event.md",
            content="missing event\n",
            producer_step="producer_without_event",
            task_id="task_missing_event",
            task_run_id="task_run_missing_event",
            validation_status="validated",
        )
    )
    validation = runtime.validate(artifact.artifact_id)

    assert validation.status == "blocked"
    assert validation.safe_to_use_as_evidence is False
    assert "producer_event_missing" in validation.missing_reasons


def test_artifact_runtime_validation_blocks_semantically_invalid_artifact() -> None:
    root = _root()
    runtime = _runtime(root)

    artifact = runtime.create(
        ArtifactRuntimeCreateRequest(
            logical_path="reports/evidence_bundle.zip",
            content="# Not an archive\n",
            content_type="application/zip",
            producer_step="evidence_step",
            task_id="task_semantic",
            task_run_id="task_run_semantic",
            event_id="task_run_event_semantic",
            validation_status="validated",
        )
    )
    validation = runtime.validate(artifact.artifact_id)

    assert validation.status == "blocked"
    assert validation.safe_to_use_as_evidence is False
    assert validation.semantic_profile is not None
    assert validation.semantic_profile.material_status == "blocked"
    assert "artifact_semantic:artifact_material_kind_mismatch" in validation.missing_reasons
