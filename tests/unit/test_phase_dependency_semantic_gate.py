from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    ReadonlyAnalysisArtifactRuntimeService,
)

from tests.unit.test_artifact_semantic_contract_music_inventory import _rich_inventory_content


class _FakeArtifactRuntime:
    def __init__(self, artifacts: dict[str, dict[str, Any]]) -> None:
        self.artifacts = artifacts

    def revalidate_public(self, artifact_id: str) -> dict[str, Any] | None:
        return self.artifacts.get(artifact_id)


def _service(tmp_path: Path, artifact: dict[str, Any]) -> ReadonlyAnalysisArtifactRuntimeService:
    phase_store = tmp_path / "readonly_analysis_artifact_phases.json"
    phase_store.write_text(
        json.dumps(
            [
                {
                    "session_id": "session_semantic_gate",
                    "phase_id": "phase_1",
                    "run_id": "task_run_phase1",
                    "workspace": "C:/Workspace/Generic",
                    "logical_paths": [artifact["logical_path"]],
                    "artifacts": [{"artifact_id": artifact["artifact_id"], "logical_path": artifact["logical_path"]}],
                    "status": "completed",
                    "created_at": "2026-08-13T00:00:00Z",
                }
            ]
        ),
        encoding="utf-8",
    )
    return ReadonlyAnalysisArtifactRuntimeService(
        artifact_runtime=_FakeArtifactRuntime({artifact["artifact_id"]: artifact}),  # type: ignore[arg-type]
        phase_store_path=phase_store,
    )


def _artifact(tmp_path: Path, *, artifact_id: str, logical_path: str, content: str) -> dict[str, Any]:
    local_path = tmp_path / f"{artifact_id}.csv"
    local_path.write_text(content, encoding="utf-8")
    return {
        "artifact_id": artifact_id,
        "logical_path": logical_path,
        "filename": Path(logical_path).name,
        "content_type": "text/csv",
        "status": "ready",
        "local_path": str(local_path),
        "metadata": {"logical_path": logical_path},
    }


def test_phase_dependency_blocks_ready_artifact_with_insufficient_semantic_contract(tmp_path: Path) -> None:
    artifact = _artifact(
        tmp_path,
        artifact_id="artifact_findings_inventory",
        logical_path="reports/media/music_inventory.csv",
        content='severity,title,summary\n"info","x","y"\n',
    )
    service = _service(tmp_path, artifact)

    result = service._validate_phase_dependencies(  # noqa: SLF001 - semantic dependency gate contract
        session_id="session_semantic_gate",
        dependency_phase_ids=["phase_1"],
    )

    assert result["status"] == "blocked"
    assert result["reason_code"] == "PHASE_DEPENDENCY_SEMANTIC_INSUFFICIENT"
    assert result["safe_to_report_success"] is False
    assert any(
        item.startswith("artifact_semantic_contract:reports/media/music_inventory.csv:media_inventory_findings_shape_mismatch")
        for item in result["missing"]
    )
    assert result["artifact_semantic_validations"][0]["status"] == "blocked"


def test_phase_dependency_passes_when_artifact_semantic_contract_is_satisfied(tmp_path: Path) -> None:
    artifact = _artifact(
        tmp_path,
        artifact_id="artifact_rich_inventory",
        logical_path="reports/media/music_inventory.csv",
        content=_rich_inventory_content(),
    )
    service = _service(tmp_path, artifact)

    result = service._validate_phase_dependencies(  # noqa: SLF001 - semantic dependency gate contract
        session_id="session_semantic_gate",
        dependency_phase_ids=["phase_1"],
    )

    assert result["status"] == "passed"
    assert result["reason_code"] is None
    assert result["safe_to_report_success"] is True
    assert result["artifact_semantic_validations"][0]["status"] == "passed"
