from __future__ import annotations

from pathlib import Path

from aipinho.schemas.runtime.task_completion import TaskCompletionEvaluation
from aipinho.schemas.runtime.task_run_request import TaskRunRequest
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.services.runtime.canonical_operation_state_service import CanonicalOperationStateService
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService
from tests.support.runtime_fixtures import allowed_policy, runtime_request


class CompletingExecutor:
    def execute_step(self, run, step, context):
        from aipinho.services.runtime.readonly_task_step_runner import TaskStepOutcome

        return TaskStepOutcome(status="completed", summary={"step_type": step.step_type})


class EmptyArtifacts:
    def by_task(self, task_id, *, limit=200):
        return []

    def get(self, artifact_id):
        return None


def test_s1_universal_session_exposes_single_canonical_state(task_runtime_service):
    task_runtime_service.loop.executor = CompletingExecutor()
    run = task_runtime_service.create_run(runtime_request())
    completed, _result = task_runtime_service.start(run.run_id)

    session = UniversalTaskSessionService(
        store=task_runtime_service.store,
        approvals=task_runtime_service.approvals,
        artifacts=EmptyArtifacts(),
    ).get_session(completed.run_id)

    assert session is not None
    canonical = session.metadata["canonical_operation_state"]
    assert canonical["status"] == session.status
    assert canonical["status"] == "COMPLETED"
    assert canonical["safe_to_report_success"] == session.result_state.safe_to_report_success
    assert canonical["safe_to_report_success"] == session.validation_state.safe_to_report_success
    assert canonical["safe_to_report_success"] is True


def test_s2_missing_required_artifact_blocks_canonical_success(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())
    run.required_artifacts = ["reports/required.md"]
    result = TaskRunResult(
        run_id=run.run_id,
        status="completed",
        summary="claimed done",
        validation={"status": "passed"},
        completion=TaskCompletionEvaluation(
            status="completed",
            safe_to_report_success=True,
            expected_outcomes=["artifact_result"],
            fulfilled_outcomes=["artifact_result"],
        ),
    )

    state = CanonicalOperationStateService().derive(run, result=result, artifacts=[])

    assert state.status == "BLOCKED"
    assert state.missing_artifacts == ["reports/required.md"]
    assert state.safe_to_report_success is False


def test_s3_workspace_context_preserves_project_and_library_roots(task_runtime_service, tmp_path: Path):
    project = tmp_path / "PinhoabacaxiMusicasDesktop"
    project.mkdir()
    library = r"D:\rafa\pinho music"
    run = task_runtime_service.create_run(
        TaskRunRequest(
            source_type="direct",
            session_id="session_multi_workspace",
            workspace=str(project),
            contract_type="analysis_readonly",
            operation_type="workspace_analysis_readonly",
            runtime_profile="readonly_analysis",
            intent_map={
                "intent_type": "workspace_analysis_readonly",
                "library_roots": [library],
                "external_roots": [str(tmp_path / "exports")],
                "readonly_flags": {str(project): True, library: True},
                "workspace_ids": ["music_library_workspace"],
            },
            policy_decision=allowed_policy(contract_type="analysis_readonly"),
            requested_actions=["read_files"],
            start_immediately=False,
        )
    )

    context = run.workspace_context

    assert context is not None
    assert context.project_root == str(project.resolve(strict=False))
    assert str(Path(library).resolve(strict=False)) in context.library_roots
    assert context.readonly_flags[str(project)] is True
    assert context.readonly_flags[library] is True
    assert "music_library_workspace" in context.workspace_ids
    assert str(Path(library).resolve(strict=False)) in context.allowed_roots


def test_s4_completion_cannot_pass_when_outputs_are_missing(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())
    result = TaskRunResult(
        run_id=run.run_id,
        status="completed",
        summary="claimed done",
        validation={"status": "passed"},
        completion=TaskCompletionEvaluation(
            status="completed",
            safe_to_report_success=True,
            expected_outcomes=["patch_result", "validation_result"],
            fulfilled_outcomes=[],
            missing_outcomes=["patch_result", "validation_result"],
        ),
    )

    state = CanonicalOperationStateService().derive(run, result=result, artifacts=[])

    assert state.status == "BLOCKED"
    assert state.safe_to_report_success is False
    assert state.missing_outputs == ["patch_result", "validation_result"]


def test_speaker_truth_required_before_canonical_state_can_complete(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())
    result = TaskRunResult(
        run_id=run.run_id,
        status="completed",
        summary="claimed done",
        validation={"status": "passed"},
        completion=TaskCompletionEvaluation(
            status="completed",
            safe_to_report_success=True,
            expected_outcomes=["validation_result"],
            fulfilled_outcomes=["validation_result"],
        ),
    )

    state = CanonicalOperationStateService().derive(run, result=result, artifacts=[])

    assert state.status == "BLOCKED"
    assert state.reason_code == "runtime_truth_required"
    assert state.safe_to_report_success is False
