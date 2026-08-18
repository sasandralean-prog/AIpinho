from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from aipinho.core.paths import PATHS
from aipinho.schemas.artifacts.artifact_runtime import ArtifactRuntimeCreateRequest
from aipinho.services.artifacts.artifact_interaction_core import ArtifactRegistryRepository
from aipinho.services.artifacts.artifact_runtime_service import ArtifactRuntimeService
from aipinho.services.artifacts.universal_artifact_registry_service import UniversalArtifactRegistryService
from aipinho.services.runtime.readonly_task_step_runner import TaskStepOutcome
from aipinho.services.runtime.runtime_timeline_service import RuntimeTimelineService
from aipinho.services.runtime.task_run_store import TaskRunStore
from aipinho.services.runtime.task_runtime_service import TaskRuntimeService
from tests.support.runtime_fixtures import runtime_request


class CompletingExecutor:
    def execute_step(self, run, step, context):
        return TaskStepOutcome(status="completed", summary={"step_type": step.step_type})


class FailingExecutor:
    def execute_step(self, run, step, context):
        return TaskStepOutcome(
            status="failed",
            summary={"step_type": step.step_type, "failed": True},
            violations=["simulated_failure"],
        )


def _artifact_runtime(root: Path):
    registry = ArtifactRegistryRepository(root / "artifact_registry.json")
    universal = UniversalArtifactRegistryService(registry=registry, store_root=root / "artifacts")
    return ArtifactRuntimeService(registry=universal), universal


def test_simple_operation_creates_runtime_timeline(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())

    timeline = task_runtime_service.get_timeline(run.run_id)

    assert timeline is not None
    assert timeline.task_id == run.task_id
    assert timeline.task_run_id == run.run_id
    assert [event.sequence for event in timeline.events] == list(range(1, len(timeline.events) + 1))
    assert {event.event_type for event in timeline.events} >= {
        "run_created",
        "task_bootstrap_created",
        "PlanningStarted",
        "PlanningFinished",
        "ExecutionPlanCreated",
    }
    assert timeline.sequence_contiguous is True


def test_multistep_operation_registers_all_step_start_and_finish(task_runtime_service):
    task_runtime_service.loop.executor = CompletingExecutor()
    run = task_runtime_service.create_run(runtime_request())

    completed, result = task_runtime_service.start(run.run_id)
    timeline = task_runtime_service.get_timeline(run.run_id)

    assert completed.status == "completed"
    assert result.status == "completed"
    assert timeline is not None
    assert len(timeline.steps) == len(completed.plan.steps)
    assert all(step.start_event_id for step in timeline.steps)
    assert all(step.finish_event_id for step in timeline.steps)
    assert all(step.complete for step in timeline.steps)
    assert timeline.completion.terminal_event_id
    assert timeline.completion.safe_to_report_success is True


def test_artifact_points_to_step_event(task_runtime_store, tmp_path):
    runtime = TaskRuntimeService(store=task_runtime_store)
    runtime.loop.executor = CompletingExecutor()
    run = runtime.create_run(runtime_request())
    completed, _result = runtime.start(run.run_id)
    timeline_before = runtime.get_timeline(run.run_id)
    first_step = timeline_before.steps[0]
    artifact_runtime, _universal = _artifact_runtime(PATHS.project_root / "data" / "tmp_runtime_timeline_tests" / uuid4().hex)

    artifact = artifact_runtime.create(
        ArtifactRuntimeCreateRequest(
            logical_path="reports/runtime_r3/artifact_link.md",
            content="# Linked artifact\n",
            content_type="text/markdown",
            artifact_type="timeline_evidence",
            producer_step=first_step.step_id,
            event_id=first_step.finish_event_id,
            task_id=completed.task_id,
            task_run_id=completed.run_id,
            validation_status="validated",
        )
    )
    timeline = RuntimeTimelineService(store=task_runtime_store, artifacts=artifact_runtime).build(completed.run_id)

    assert timeline is not None
    linked = next(item for item in timeline.artifacts if item.artifact_id == artifact.artifact_id)
    assert linked.event_id == first_step.finish_event_id
    assert linked.producer_step == first_step.step_id
    assert linked.orphan is False
    assert artifact.artifact_id in timeline.steps[0].artifacts


def test_validation_is_registered_as_timeline_event(task_runtime_service):
    task_runtime_service.loop.executor = CompletingExecutor()
    run = task_runtime_service.create_run(runtime_request())

    task_runtime_service.start(run.run_id)
    timeline = task_runtime_service.get_timeline(run.run_id)

    assert timeline is not None
    assert timeline.validations
    assert timeline.validations[0].event_id
    assert timeline.validations[0].status in {"passed", "completed", "validated"}
    assert any(event.event_type == "task_completion_evaluated" for event in timeline.events)


def test_failed_operation_timeline_ends_failed_without_gaps(task_runtime_service):
    task_runtime_service.loop.executor = FailingExecutor()
    run = task_runtime_service.create_run(runtime_request())

    failed, result = task_runtime_service.start(run.run_id)
    timeline = task_runtime_service.get_timeline(run.run_id)

    assert failed.status == "failed"
    assert result.status == "failed"
    assert timeline is not None
    assert timeline.completion.status == "failed"
    assert timeline.completion.terminal_event_id
    assert any(event.event_type == "run_failed" for event in timeline.events)
    assert timeline.sequence_contiguous is True
    assert timeline.completion.safe_to_report_success is False


def test_timeline_sequence_is_contiguous_for_multiple_steps(task_runtime_service):
    task_runtime_service.loop.executor = CompletingExecutor()
    run = task_runtime_service.create_run(runtime_request())

    task_runtime_service.start(run.run_id)
    timeline = task_runtime_service.get_timeline(run.run_id)

    assert timeline is not None
    assert timeline.sequence_contiguous is True
    assert [event.sequence for event in timeline.events] == list(range(1, len(timeline.events) + 1))


def test_timeline_can_audit_reloaded_task_run(task_runtime_store):
    runtime = TaskRuntimeService(store=task_runtime_store)
    runtime.loop.executor = CompletingExecutor()
    run = runtime.create_run(runtime_request())
    runtime.start(run.run_id)
    reloaded_store = TaskRunStore(root=task_runtime_store.root)

    timeline = RuntimeTimelineService(store=reloaded_store).build(run.run_id)

    assert timeline is not None
    assert timeline.task_run_id == run.run_id
    assert timeline.task_id == run.task_id
    assert timeline.events
    assert timeline.completion.status == "completed"
