from __future__ import annotations

import json
import time
from pathlib import Path
from uuid import uuid4

from aipinho.schemas.chat.chat_request import ChatRequest
from aipinho.services.governance.runtime.readonly_analysis_artifact_runtime_service import (
    PublicRuntimeResponsePolicy,
    ReadonlyAnalysisArtifactRuntimeService,
)


class _DependencyArtifactRuntime:
    def __init__(self) -> None:
        self.revalidate_calls = 0

    def revalidate_public(self, artifact_id: str):
        self.revalidate_calls += 1
        return {
            "artifact_id": artifact_id,
            "status": "ready",
            "logical_path": "reports/example/dependency.csv",
            "metadata": {"logical_path": "reports/example/dependency.csv"},
        }


class _SlowSemanticDependencyRuntime(ReadonlyAnalysisArtifactRuntimeService):
    def _validate_artifact_semantic_contract(self, logical_path: str, artifact: dict):  # noqa: ANN001
        time.sleep(0.2)
        return {
            "logical_path": logical_path,
            "status": "blocked",
            "missing_requirements": ["semantic_dependency_not_satisfied"],
            "profile": {},
        }


def _write_phase_store(path: Path, session_id: str) -> None:
    path.write_text(
        json.dumps(
            [
                {
                    "session_id": session_id,
                    "phase_id": "phase_1",
                    "run_id": f"task_run_{uuid4().hex}",
                    "workspace": r"C:\Workspace\Generic",
                    "logical_paths": ["reports/example/phase1.md"],
                    "artifacts": [{"artifact_id": "artifact_phase1", "logical_path": "reports/example/phase1.md"}],
                    "status": "completed",
                    "created_at": "2026-08-13T00:00:00+00:00",
                },
                {
                    "session_id": session_id,
                    "phase_id": "phase_2",
                    "run_id": f"task_run_{uuid4().hex}",
                    "workspace": r"C:\Workspace\Generic",
                    "logical_paths": ["reports/example/phase2.md"],
                    "artifacts": [{"artifact_id": "artifact_phase2", "logical_path": "reports/example/phase2.md"}],
                    "status": "completed",
                    "created_at": "2026-08-13T00:01:00+00:00",
                },
            ],
            indent=2,
        ),
        encoding="utf-8",
    )


def test_phase3_accepts_taskrun_before_heavy_dependency_semantic_validation(task_runtime_service, tmp_path) -> None:
    session_id = "chat_phase3_preacceptance"
    phase_store = tmp_path / "phase_store.json"
    _write_phase_store(phase_store, session_id)
    artifact_runtime = _DependencyArtifactRuntime()
    service = _SlowSemanticDependencyRuntime(
        runtime=task_runtime_service,
        artifact_runtime=artifact_runtime,
        phase_store_path=phase_store,
        public_response_policy=PublicRuntimeResponsePolicy(initial_response_budget_ms=50),
    )
    request = ChatRequest(
        session_id=session_id,
        message=(
            "Fase 3 Experimental Diagnosis depende dos artefatos anteriores. "
            "Gerar reports/example/phase3_experimental.md."
        ),
    )

    started = time.monotonic()
    execution = service.start_public_boundary(request=request, workspace=r"C:\Workspace\Generic")
    elapsed_ms = int((time.monotonic() - started) * 1000)

    assert elapsed_ms < 500
    assert execution.response.status == "accepted_running"
    assert execution.response.task_run_id
    assert execution.run_id == execution.response.task_run_id
    assert execution.response.result_ref_id == execution.response.task_run_id
    assert execution.response.governance_lifecycle["public_response_boundary"]["safe_to_report_success"] is False


def test_phase3_dependency_semantic_failure_is_recorded_inside_taskrun(task_runtime_service, tmp_path) -> None:
    session_id = "chat_phase3_dependency_inside_run"
    phase_store = tmp_path / "phase_store.json"
    _write_phase_store(phase_store, session_id)
    service = _SlowSemanticDependencyRuntime(
        runtime=task_runtime_service,
        artifact_runtime=_DependencyArtifactRuntime(),
        phase_store_path=phase_store,
        public_response_policy=PublicRuntimeResponsePolicy(initial_response_budget_ms=50),
    )
    request = ChatRequest(
        session_id=session_id,
        message=(
            "Fase 3 Experimental Diagnosis depende dos artefatos anteriores. "
            "Gerar reports/example/phase3_experimental.md."
        ),
    )

    execution = service.start_public_boundary(request=request, workspace=r"C:\Workspace\Generic")
    deadline = time.monotonic() + 2.0
    result = None
    while time.monotonic() < deadline:
        result = task_runtime_service.store.get_result(execution.run_id)
        if result is not None:
            break
        time.sleep(0.05)

    run = task_runtime_service.store.get_run(execution.run_id)
    events = task_runtime_service.store.get_events(execution.run_id)
    assert run is not None
    assert result is not None
    assert run.status == "blocked"
    assert result.status == "blocked"
    assert result.outputs["validation_result"]["reason_code"] == "PHASE_DEPENDENCY_SEMANTIC_INSUFFICIENT"
    assert result.outputs["validation_result"]["safe_to_report_success"] is False
    assert len([event for event in events if event.type == "run_blocked"]) == 1
