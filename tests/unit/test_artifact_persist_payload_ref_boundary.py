from __future__ import annotations

from pathlib import Path

import pytest

from aipinho.schemas.artifacts.artifact_interaction_contracts import ArtifactRecord, UniversalArtifactCreateRequest
from aipinho.core.paths import PATHS
from aipinho.services.artifacts.artifact_interaction_core import ArtifactRegistryRepository
from aipinho.services.artifacts.universal_artifact_registry_service import UniversalArtifactRegistryService


def _service(tmp_path: Path) -> UniversalArtifactRegistryService:
    root = PATHS.project_root / ".tmp_pytest_artifact_persist" / tmp_path.name
    return UniversalArtifactRegistryService(
        registry=ArtifactRegistryRepository(tmp_path / "manifests" / "artifact_registry.json"),
        store_root=root / "universal",
        index_root=root / "index",
    )


def test_large_manifest_payload_is_ref_backed_without_changing_artifact_content(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_ARTIFACT_MANIFEST_INLINE_MAX_BYTES", "1024")
    service = _service(tmp_path)
    stages: list[tuple[str, dict]] = []

    record = service.create(
        UniversalArtifactCreateRequest(
            source_agent="test_agent",
            filename="generic_report.txt",
            logical_path="reports/generic_report.txt",
            task_id="task_generic",
            task_run_id="task_run_generic",
            producer_step="generic_runtime",
            content="small artifact body",
            metadata={"large_semantic_payload": {"items": ["x" * 100 for _ in range(200)]}},
            provenance={"source": "generic_fixture"},
        ),
        progress_observer=lambda stage, metrics: stages.append((stage, dict(metrics))),
    )

    ref = record.metadata["large_semantic_payload"]
    assert ref["reason_code"] == "ARTIFACT_MANIFEST_PAYLOAD_SPILLED_TO_REF"
    assert ref["byte_size"] > 1024
    assert Path(ref["content_ref"]).is_absolute() is False
    assert (PATHS.project_root / ref["content_ref"]).exists()
    assert Path(record.local_path).read_text(encoding="utf-8") == "small artifact body"
    assert any(stage == "before_payload_ref_persist" for stage, _ in stages)
    assert any(stage == "after_artifact_commit" for stage, _ in stages)


def test_duplicate_manifest_subtrees_reuse_payload_ref_by_digest(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_ARTIFACT_MANIFEST_INLINE_MAX_BYTES", "1024")
    service = _service(tmp_path)
    duplicated = {"items": ["same" * 50 for _ in range(200)]}
    stages: list[tuple[str, dict]] = []

    record = service.create(
        UniversalArtifactCreateRequest(
            source_agent="test_agent",
            filename="dedup.txt",
            logical_path="reports/dedup.txt",
            task_id="task_generic",
            task_run_id="task_run_generic",
            producer_step="generic_runtime",
            content="small artifact body",
            metadata={"large_a": duplicated},
            provenance={"large_b": duplicated},
        ),
        progress_observer=lambda stage, metrics: stages.append((stage, dict(metrics))),
    )

    ref_a = record.metadata["large_a"]
    ref_b = record.provenance["large_b"]
    ref_files = list((PATHS.project_root / ref_a["content_ref"]).parent.glob("*.json"))

    assert ref_a["sha256"] == ref_b["sha256"]
    assert ref_b["dedup_hit"] is True
    assert len(ref_files) == 1
    assert any(stage == "payload_ref_dedup_hit" for stage, _ in stages)


def test_small_manifest_payload_remains_inline(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_ARTIFACT_MANIFEST_INLINE_MAX_BYTES", "100000")
    service = _service(tmp_path)

    record = service.create(
        UniversalArtifactCreateRequest(
            source_agent="test_agent",
            filename="small.txt",
            logical_path="reports/small.txt",
            task_id="task_generic",
            task_run_id="task_run_generic",
            producer_step="generic_runtime",
            content="body",
            metadata={"summary": {"status": "small"}},
        )
    )

    assert record.metadata["summary"] == {"status": "small"}
    assert "payload_ref_id" not in record.metadata["summary"]


class FailingRegistry(ArtifactRegistryRepository):
    def save(self, record: ArtifactRecord, *, progress_observer=None) -> ArtifactRecord:  # type: ignore[override]
        raise OSError("manifest_write_failed")


def test_manifest_failure_does_not_leave_committed_artifact_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AIPINHO_ARTIFACT_MANIFEST_INLINE_MAX_BYTES", "1024")
    service = UniversalArtifactRegistryService(
        registry=FailingRegistry(tmp_path / "manifests" / "artifact_registry.json"),
        store_root=PATHS.project_root / ".tmp_pytest_artifact_persist" / tmp_path.name / "universal",
        index_root=tmp_path / "index",
    )

    with pytest.raises(OSError):
        service.create(
            UniversalArtifactCreateRequest(
                source_agent="test_agent",
                filename="fail.txt",
                logical_path="reports/fail.txt",
                task_id="task_generic",
                task_run_id="task_run_generic",
                producer_step="generic_runtime",
                content="body",
            )
        )

    assert list((PATHS.project_root / ".tmp_pytest_artifact_persist" / tmp_path.name / "universal").glob("*fail.txt")) == []
