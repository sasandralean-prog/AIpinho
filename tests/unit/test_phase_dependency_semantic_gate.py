from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    ReadonlyAnalysisArtifactRuntimeService,
)
from aipinho.schemas.runtime.phase_dependency_evaluation import DownstreamPhaseRequirements
from aipinho.services.runtime.phase_dependency_contract_registry import PhaseDependencyContractRegistry

from tests.unit.test_artifact_semantic_contract_music_inventory import _rich_inventory_content


class _FakeArtifactRuntime:
    def __init__(self, artifacts: dict[str, dict[str, Any]]) -> None:
        self.artifacts = artifacts

    def revalidate_public(self, artifact_id: str) -> dict[str, Any] | None:
        return self.artifacts.get(artifact_id)


def _service(
    tmp_path: Path,
    artifact: dict[str, Any],
    *,
    phase_status: str = "completed",
    phase_dependency: dict[str, Any] | None = None,
    use_safety: dict[str, Any] | None = None,
) -> ReadonlyAnalysisArtifactRuntimeService:
    phase_store = tmp_path / "readonly_analysis_artifact_phases.json"
    phase_store.write_text(
        json.dumps(
            [
                {
                    "session_id": "session_semantic_gate",
                    "phase_id": "phase_1",
                    "run_id": "task_run_phase1",
                    "operation_id": "operation_phase1",
                    "result_ref": "task_run_result:task_run_phase1",
                    "workspace": "C:/Workspace/Generic",
                    "logical_paths": [artifact["logical_path"]],
                    "artifacts": [{"artifact_id": artifact["artifact_id"], "logical_path": artifact["logical_path"]}],
                    "status": phase_status,
                    "phase_dependency": phase_dependency or {"status": "satisfied"},
                    "use_safety": use_safety or {},
                    "evidence_refs": ["artifact:" + artifact["artifact_id"]],
                    "created_at": "2026-08-13T00:00:00Z",
                }
            ]
        ),
        encoding="utf-8",
    )
    return ReadonlyAnalysisArtifactRuntimeService(
        artifact_runtime=_FakeArtifactRuntime({artifact["artifact_id"]: artifact}),  # type: ignore[arg-type]
        phase_store_path=phase_store,
        phase_dependency_contracts=PhaseDependencyContractRegistry(
            [
                DownstreamPhaseRequirements(
                    contract_id="generic_phase_2",
                    consumer_phase_id="phase_2",
                    operation_type="readonly_analysis_with_artifact_output",
                    evidence_required=True,
                )
            ]
        ),
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
        consumer_task_run_id="task_run_phase2",
        consumer_operation_id="operation_phase2",
        consumer_phase_id="phase_2",
        consumer_operation_type="readonly_analysis_with_artifact_output",
        downstream_requirements=service.phase_dependency_contracts.resolve_invariants(
            "phase_2", "readonly_analysis_with_artifact_output"
        ),
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
        consumer_task_run_id="task_run_phase2",
        consumer_operation_id="operation_phase2",
        consumer_phase_id="phase_2",
        consumer_operation_type="readonly_analysis_with_artifact_output",
        downstream_requirements=service.phase_dependency_contracts.resolve_invariants(
            "phase_2", "readonly_analysis_with_artifact_output"
        ),
    )

    assert result["status"] == "passed"
    assert result["reason_code"] is None
    assert result["safe_to_report_success"] is True
    assert result["dependency_evaluation_status"] == "passed"
    assert result["dependency_evaluations"][0]["authorized"] is True
    assert result["artifact_semantic_validations"][0]["status"] == "passed"


def test_phase_dependency_admits_partial_artifact_only_for_explicit_limited_use(tmp_path: Path) -> None:
    artifact = _artifact(
        tmp_path,
        artifact_id="artifact_limited_inventory",
        logical_path="reports/media/music_inventory.csv",
        content=_rich_inventory_content(),
    )
    artifact["status"] = "partial"
    service = _service(
        tmp_path,
        artifact,
        phase_status="completed_with_limitations",
        phase_dependency={
            "status": "satisfied_with_limitations",
            "allowed_downstream_uses": ["catalog_planning_with_limitations"],
            "forbidden_downstream_claims": ["full_truth"],
        },
        use_safety={
            "safe_for_truth_claim": False,
            "safe_for_catalog": True,
            "safe_for_planning": "true_with_limitations",
            "safe_for_destructive_action": False,
        },
    )
    requirements = DownstreamPhaseRequirements(
        contract_id="limited_phase_2",
        consumer_phase_id="phase_2",
        operation_type="readonly_analysis_with_artifact_output",
        allowed_dependency_statuses=["satisfied_with_limitations"],
        required_downstream_uses=["catalog_planning_with_limitations"],
        required_use_safety={
            "safe_for_catalog": [True],
            "safe_for_planning": ["true_with_limitations"],
        },
        evidence_required=True,
    )

    result = service._validate_phase_dependencies(  # noqa: SLF001 - scoped limited-use contract
        session_id="session_semantic_gate",
        dependency_phase_ids=["phase_1"],
        consumer_task_run_id="task_run_phase2",
        consumer_operation_id="operation_phase2",
        consumer_phase_id="phase_2",
        consumer_operation_type="readonly_analysis_with_artifact_output",
        downstream_requirements=requirements,
    )

    assert result["status"] == "passed"
    assert result["dependency_evaluations"][0]["decision"] == "ADMITTED_WITH_CONSTRAINTS"
    assert result["dependency_evaluations"][0]["authorized"] is True
    assert result["artifacts"][0]["status"] == "partial"
    assert result["artifacts"][0]["dependency_artifact_scope"] == "producer_outcome_limited_use"


def test_phase_dependency_without_compiled_downstream_demand_fails_closed(tmp_path: Path) -> None:
    artifact = _artifact(
        tmp_path,
        artifact_id="artifact_no_downstream_contract",
        logical_path="reports/media/music_inventory.csv",
        content=_rich_inventory_content(),
    )
    service = _service(tmp_path, artifact)
    service.phase_dependency_contracts = PhaseDependencyContractRegistry()

    result = service._validate_phase_dependencies(  # noqa: SLF001 - admission boundary contract
        session_id="session_semantic_gate",
        dependency_phase_ids=["phase_1"],
        consumer_task_run_id="task_run_phase2",
        consumer_operation_id="operation_phase2",
        consumer_phase_id="phase_2",
        consumer_operation_type="readonly_analysis_with_artifact_output",
    )

    assert result["status"] == "blocked"
    assert result["reason_code"] == "PHASE_DEPENDENCY_INSUFFICIENT_CONTRACT_EVIDENCE"
    assert result["dependency_evaluations"][0]["decision"] == "NOT_EVALUATED"
    assert result["dependency_evaluations"][0]["authorized"] is False


def test_phase_dependency_does_not_fall_back_to_another_session(tmp_path: Path) -> None:
    artifact = _artifact(
        tmp_path,
        artifact_id="artifact_other_session",
        logical_path="reports/media/music_inventory.csv",
        content=_rich_inventory_content(),
    )
    service = _service(tmp_path, artifact)

    result = service._validate_phase_dependencies(  # noqa: SLF001 - cross-session authority regression
        session_id="different_session",
        dependency_phase_ids=["phase_1"],
        consumer_task_run_id="task_run_phase2",
        consumer_operation_id="operation_phase2",
        consumer_phase_id="phase_2",
        consumer_operation_type="readonly_analysis_with_artifact_output",
    )

    assert result["status"] == "blocked"
    assert result["missing"] == ["phase:phase_1"]
    assert result["dependency_evaluations"] == []
