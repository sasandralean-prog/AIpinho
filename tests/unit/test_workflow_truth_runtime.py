from __future__ import annotations

from aipinho.schemas.runtime.task_completion import TaskCompletionEvaluation
from aipinho.schemas.runtime.phase_dependency_evaluation import (
    DownstreamPhaseRequirements,
    PhaseSemanticDemandCompilation,
)
from aipinho.schemas.runtime.runtime_timeline import (
    RuntimeTimeline,
    RuntimeTimelineArtifact,
    RuntimeTimelineCompletion,
    RuntimeTimelineEvent,
)
from aipinho.schemas.runtime.task_run_plan import TaskRunPlan
from aipinho.schemas.runtime.task_run_result import TaskRunResult
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.services.runtime.runtime_truth_engine import RuntimeTruthEngine
from aipinho.services.runtime.workflow_runtime_service import WorkflowRuntimeService
from aipinho.services.runtime.readonly_task_step_runner import TaskStepOutcome
from aipinho.services.runtime.universal_task_session_service import UniversalTaskSessionService
from aipinho.services.speaker.task_speaker_update_service import TaskSpeakerUpdateService
from tests.support.runtime_fixtures import runtime_request


class CompletingExecutor:
    def execute_step(self, run, step, context):
        return TaskStepOutcome(status="completed", summary={"step_type": step.step_type})


class _StaticDemandCompiler:
    def __init__(self, requirements: DownstreamPhaseRequirements) -> None:
        self.requirements = requirements
        self.calls = 0

    def compile_for_run(
        self,
        *,
        run,
        consumer_phase_id: str,
        consumer_operation_type: str,
        source_step_id: str,
    ) -> PhaseSemanticDemandCompilation:
        self.calls += 1
        requirements = self.requirements.model_copy(
            update={
                "consumer_phase_id": consumer_phase_id,
                "operation_type": consumer_operation_type,
            }
        )
        return PhaseSemanticDemandCompilation(
            status="compiled",
            consumer_phase_id=consumer_phase_id,
            consumer_operation_type=consumer_operation_type,
            requirements=requirements,
            semantic_interpretation={"status": "fixture"},
        )


def _workflow_with_explicit_first_dependency(
    run,
    requirements: DownstreamPhaseRequirements,
):
    canonical = run.plan.canonical_execution_plan
    assert canonical is not None
    assert len(canonical.execution_steps) >= 2
    first = canonical.execution_steps[0]
    second = canonical.execution_steps[1]
    second.depends_on = [first.step_id]
    compiler = _StaticDemandCompiler(requirements)
    service = WorkflowRuntimeService(
        semantic_demand_compiler=compiler,  # type: ignore[arg-type]
    )
    workflow = service.create_for_run(run)
    return service, workflow, compiler


def test_r4_workflow_is_created_for_task_run(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())

    assert run.workflow is not None
    assert run.workflow.workflow_id.startswith("workflow_")
    assert run.workflow.task_run_id == run.run_id
    assert len(run.workflow.phases) == len(run.plan.steps)
    assert all(phase.steps == ["START", "EXECUTION", "VALIDATION", "FINISH"] for phase in run.workflow.phases)


def test_r4_multiphase_workflow_transitions_and_progress(task_runtime_service):
    task_runtime_service.loop.executor = CompletingExecutor()
    run = task_runtime_service.create_run(runtime_request())

    completed, result = task_runtime_service.start(run.run_id)

    assert result.status == "completed"
    assert completed.workflow is not None
    assert completed.workflow.status == "completed"
    assert completed.workflow.progress == 100
    assert all(phase.status == "completed" for phase in completed.workflow.phases)
    assert all(phase.validation_status == "passed" for phase in completed.workflow.phases)


def test_r4_phase_cannot_finish_without_validation_checkpoint(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())
    workflow = run.workflow
    phase = workflow.phases[0]
    phase.checkpoints = [item for item in phase.checkpoints if item.checkpoint_type != "VALIDATION"]
    phase.status = "completed"

    issues = [
        f"{phase.phase_id}:validation_missing"
        for phase in workflow.phases
        if phase.status in {"completed", "partial"} and not any(item.checkpoint_type == "VALIDATION" for item in phase.checkpoints)
    ]

    assert issues == [f"{phase.phase_id}:validation_missing"]


def test_r5_implicit_sequence_allows_next_phase_without_semantic_admission(
    task_runtime_service,
):
    task_runtime_service.loop.executor = CompletingExecutor()
    run = task_runtime_service.create_run(runtime_request())

    completed, _result = task_runtime_service.start(run.run_id)
    deps = completed.workflow.dependencies

    assert deps
    assert all(dep.status == "completed" for dep in deps)
    assert all(not dep.missing_reasons for dep in deps)
    assert all(dep.relation == "implicit_sequence" for dep in deps)
    assert all(dep.evaluation_required is False for dep in deps)
    assert all(dep.demand_compilation is None for dep in deps)
    assert all(dep.evaluation is None for dep in deps)
    assert all(dep.admission is None for dep in deps)


def test_r5_partial_phase_without_violations_can_feed_next_phase(
    task_runtime_service,
):
    run = task_runtime_service.create_run(runtime_request())
    workflow = run.workflow
    assert workflow is not None
    service = WorkflowRuntimeService()
    producer = workflow.phases[0]
    consumer = workflow.phases[1]

    service.start_phase_for_step(
        workflow,
        producer.source_step_id,
    )
    service.finish_phase_for_step(
        workflow,
        producer.source_step_id,
        status="partial",
        validation_ref="validation_partial_context",
        violations=[],
    )

    assert producer.status == "partial"
    assert producer.validation_status == "passed"

    allowed, reasons = service.can_start_phase(
        workflow,
        consumer.source_step_id,
    )

    assert allowed is True
    assert reasons == []
    dependency = next(
        item
        for item in workflow.dependencies
        if item.producer_phase_id == producer.phase_id
        and item.consumer_phase_id == consumer.phase_id
    )
    assert dependency.status == "completed"
    assert dependency.relation == "implicit_sequence"
    assert dependency.evaluation_required is False
    assert dependency.demand_compilation is None
    assert dependency.evaluation is None
    assert dependency.admission is None



def test_r5_partial_phase_semantic_outcome_is_preserved_for_dependency_admission(
    task_runtime_service,
):
    run = task_runtime_service.create_run(runtime_request())
    requirements = DownstreamPhaseRequirements(
        contract_id="workflow_partial_static_analysis",
        consumer_phase_id="pending",
        operation_type="pending",
        authority_source="workflow_contract",
        allowed_dependency_statuses=[
            "satisfied",
            "satisfied_with_limitations",
        ],
        required_use_safety={
            "safe_for_downstream_static_analysis": [
                True,
                "true_with_limitations",
            ]
        },
        evidence_required=True,
    )
    service, workflow, compiler = _workflow_with_explicit_first_dependency(
        run,
        requirements,
    )
    producer = workflow.phases[0]
    consumer = workflow.phases[1]
    dependency = next(
        item
        for item in workflow.dependencies
        if item.producer_phase_id == producer.phase_id
        and item.consumer_phase_id == consumer.phase_id
    )
    assert dependency.relation == "explicit_plan_dependency"
    assert dependency.evaluation_required is True
    assert dependency.demand_compilation is not None
    assert dependency.requirements is not None
    assert compiler.calls == 1

    service.start_phase_for_step(workflow, producer.source_step_id)
    service.finish_phase_for_step(
        workflow,
        producer.source_step_id,
        status="partial",
        validation_ref="validation_partial_context_semantics",
        violations=[],
        semantic_outcome={
            "use_safety": {
                "safe_for_downstream_static_analysis": (
                    "true_with_limitations"
                )
            },
        },
    )

    assert producer.semantic_outcome["use_safety"][
        "safe_for_downstream_static_analysis"
    ] == "true_with_limitations"

    allowed, reasons = service.can_start_phase(
        workflow,
        consumer.source_step_id,
    )

    assert allowed is True
    assert reasons == []
    assert dependency.evaluation is not None
    safety_check = next(
        check
        for check in dependency.evaluation.requirement_checks
        if check.requirement
        == "use_safety:safe_for_downstream_static_analysis"
    )
    assert safety_check.expected == [True, "true_with_limitations"]
    assert safety_check.observed == "true_with_limitations"
    assert safety_check.status == "satisfied"
    assert dependency.admission is not None
    assert dependency.admission.authorized is True



def test_r5_partial_analysis_semantic_outcome_is_preserved_for_report_dependency(
    task_runtime_service,
):
    run = task_runtime_service.create_run(runtime_request())
    requirements = DownstreamPhaseRequirements(
        contract_id="workflow_partial_project_report",
        consumer_phase_id="pending",
        operation_type="pending",
        authority_source="workflow_contract",
        allowed_dependency_statuses=[
            "satisfied",
            "satisfied_with_limitations",
        ],
        required_use_safety={
            "safe_for_user_report": [
                True,
                "true_with_limitations",
            ]
        },
        evidence_required=True,
    )
    service, workflow, compiler = _workflow_with_explicit_first_dependency(
        run,
        requirements,
    )
    producer = workflow.phases[0]
    consumer = workflow.phases[1]
    dependency = next(
        item
        for item in workflow.dependencies
        if item.producer_phase_id == producer.phase_id
        and item.consumer_phase_id == consumer.phase_id
    )
    assert dependency.relation == "explicit_plan_dependency"
    assert dependency.evaluation_required is True
    assert dependency.demand_compilation is not None
    assert dependency.requirements is not None
    assert compiler.calls == 1

    service.start_phase_for_step(workflow, producer.source_step_id)
    service.finish_phase_for_step(
        workflow,
        producer.source_step_id,
        status="partial",
        validation_ref="validation_partial_analysis_semantics",
        violations=[],
        semantic_outcome={
            "use_safety": {
                "safe_for_user_report": "true_with_limitations",
            },
        },
    )

    allowed, reasons = service.can_start_phase(
        workflow,
        consumer.source_step_id,
    )

    assert allowed is True
    assert reasons == []
    assert dependency.evaluation is not None
    safety_check = next(
        check
        for check in dependency.evaluation.requirement_checks
        if check.requirement == "use_safety:safe_for_user_report"
    )
    assert safety_check.expected == [True, "true_with_limitations"]
    assert safety_check.observed == "true_with_limitations"
    assert safety_check.status == "satisfied"
    assert dependency.admission is not None
    assert dependency.admission.authorized is True


def test_r5_explicit_semantic_dependency_without_required_safety_fails_closed(
    task_runtime_service,
):
    run = task_runtime_service.create_run(runtime_request())
    requirements = DownstreamPhaseRequirements(
        contract_id="workflow_explicit_static_analysis",
        consumer_phase_id="pending",
        operation_type="pending",
        authority_source="workflow_contract",
        allowed_dependency_statuses=["satisfied", "satisfied_with_limitations"],
        required_use_safety={
            "safe_for_downstream_static_analysis": [
                True,
                "true_with_limitations",
            ]
        },
        evidence_required=True,
    )
    service, workflow, _compiler = _workflow_with_explicit_first_dependency(
        run,
        requirements,
    )
    producer = workflow.phases[0]
    consumer = workflow.phases[1]
    dependency = next(
        item
        for item in workflow.dependencies
        if item.producer_phase_id == producer.phase_id
        and item.consumer_phase_id == consumer.phase_id
    )

    service.start_phase_for_step(workflow, producer.source_step_id)
    service.finish_phase_for_step(
        workflow,
        producer.source_step_id,
        status="completed",
        validation_ref="validation_explicit_without_safety",
        violations=[],
        semantic_outcome={},
    )

    allowed, reasons = service.can_start_phase(
        workflow,
        consumer.source_step_id,
    )

    assert allowed is False
    assert dependency.relation == "explicit_plan_dependency"
    assert dependency.evaluation_required is True
    assert dependency.evaluation is not None
    assert dependency.evaluation.evaluation_status == "incomplete"
    assert "PHASE_DEPENDENCY_REQUIRED_USE_SAFETY_UNKNOWN" in (
        dependency.evaluation.reason_codes
    )
    assert dependency.admission is not None
    assert dependency.admission.authorized is False
    assert any(
        "PHASE_DEPENDENCY_EVALUATION_INCOMPLETE" in reason
        for reason in reasons
    )


def test_r5_nonadjacent_explicit_dependency_is_materialized_semantically(
    task_runtime_service,
):
    run = task_runtime_service.create_run(runtime_request())
    canonical = run.plan.canonical_execution_plan
    assert canonical is not None
    assert len(canonical.execution_steps) >= 3
    first = canonical.execution_steps[0]
    third = canonical.execution_steps[2]
    third.depends_on = [first.step_id]
    requirements = DownstreamPhaseRequirements(
        contract_id="workflow_nonadjacent_dependency",
        consumer_phase_id="pending",
        operation_type="pending",
        authority_source="workflow_contract",
        allowed_dependency_statuses=["satisfied", "satisfied_with_limitations"],
        evidence_required=True,
    )
    compiler = _StaticDemandCompiler(requirements)
    service = WorkflowRuntimeService(
        semantic_demand_compiler=compiler,  # type: ignore[arg-type]
    )
    workflow = service.create_for_run(run)
    phase_by_step = {
        phase.source_step_id: phase
        for phase in workflow.phases
    }
    explicit = next(
        item
        for item in workflow.dependencies
        if item.producer_phase_id == phase_by_step[first.step_id].phase_id
        and item.consumer_phase_id == phase_by_step[third.step_id].phase_id
    )

    assert explicit.relation == "explicit_plan_dependency"
    assert explicit.evaluation_required is True
    assert explicit.demand_compilation is not None
    assert compiler.calls == 1
    implicit = [
        item
        for item in workflow.dependencies
        if item.relation == "implicit_sequence"
    ]
    assert len(implicit) == len(workflow.phases) - 1
    assert phase_by_step[first.step_id].phase_id in phase_by_step[
        third.step_id
    ].depends_on


def test_r5_missing_artifact_dependency_blocks_phase(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())
    workflow = run.workflow
    assert workflow is not None and workflow.dependencies
    dependency = workflow.dependencies[0]
    dependency.required_artifacts = ["artifact_required_for_phase_2"]

    allowed, reasons = WorkflowRuntimeService().can_start_phase(workflow, dependency.consumer_phase_id.replace("phase_", "missing_step_"))
    assert allowed is False
    assert "workflow_phase_not_found" in reasons

    consumer = WorkflowRuntimeService().phase(workflow, dependency.consumer_phase_id)
    allowed, reasons = WorkflowRuntimeService().can_start_phase(workflow, consumer.source_step_id)

    assert allowed is False
    assert "missing_required_phase_dependencies" in reasons
    assert any("artifact_missing:artifact_required_for_phase_2" in reason for reason in reasons)


def test_r5_resume_point_is_deterministic(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())
    workflow = run.workflow
    first = workflow.phases[0]
    WorkflowRuntimeService().start_phase_for_step(workflow, first.source_step_id)
    WorkflowRuntimeService().finish_phase_for_step(workflow, first.source_step_id, status="completed", validation_ref="validation_phase_1")

    resume = WorkflowRuntimeService().resume_point(workflow)

    assert resume is not None
    assert resume.phase_id == workflow.phases[1].phase_id
    assert resume.source_step_id == workflow.phases[1].source_step_id


def test_r6_truth_blocks_completion_when_workflow_is_blocked(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())
    run.workflow.status = "blocked"
    result = TaskRunResult(
        run_id=run.run_id,
        status="completed",
        summary="claimed complete",
        completion=TaskCompletionEvaluation(status="completed", safe_to_report_success=True),
        validation={"status": "passed"},
    )
    timeline = task_runtime_service.get_timeline(run.run_id)

    truth = RuntimeTruthEngine().evaluate(run, result=result, timeline=timeline)

    assert truth.status == "blocked"
    assert truth.safe_to_report_success is False
    assert "completion_completed_workflow_blocking" in truth.contradictions


def test_r6_truth_blocks_success_when_timeline_has_orphan_artifact(task_runtime_service):
    run = task_runtime_service.create_run(runtime_request())
    result = TaskRunResult(
        run_id=run.run_id,
        status="completed",
        summary="claimed complete",
        completion=TaskCompletionEvaluation(status="completed", safe_to_report_success=True),
        validation={"status": "passed"},
    )
    timeline = RuntimeTimeline(
        timeline_id=f"timeline_{run.run_id}",
        task_id=run.task_id,
        task_run_id=run.run_id,
        status="completed",
        events=[
            RuntimeTimelineEvent(
                event_id="event_terminal",
                sequence=1,
                timestamp="2026-07-31T00:00:00+00:00",
                task_id=run.task_id,
                task_run_id=run.run_id,
                event_type="run_completed",
                status="completed",
            )
        ],
        artifacts=[
            RuntimeTimelineArtifact(
                artifact_id="artifact_orphan",
                logical_path="reports/orphan.md",
                status="ready",
                orphan=True,
                orphan_reasons=["producer_event_missing"],
            )
        ],
        completion=RuntimeTimelineCompletion(
            status="completed",
            safe_to_report_success=True,
            terminal_event_id="event_terminal",
        ),
        gaps=["artifact:artifact_orphan:producer_event_missing"],
        orphan_artifact_ids=["artifact_orphan"],
    )

    truth = RuntimeTruthEngine().evaluate(run, result=result, timeline=timeline)

    assert truth.status == "blocked"
    assert truth.safe_to_report_success is False
    assert "completion_completed_artifact_orphans" in truth.contradictions
    assert "artifact:artifact_orphan:producer_binding" in truth.missing_evidence


def test_r6_universal_session_uses_runtime_truth(task_runtime_service):
    task_runtime_service.loop.executor = CompletingExecutor()
    run = task_runtime_service.create_run(runtime_request())
    completed, _result = task_runtime_service.start(run.run_id)
    service = UniversalTaskSessionService(store=task_runtime_service.store, approvals=task_runtime_service.approvals)

    session = service.get_session(completed.run_id)

    assert session.status == "COMPLETED"
    assert session.progress.basis == "workflow_phases"
    assert session.metadata["runtime_truth"]["status"] == "completed"
    assert session.metadata["runtime_truth"]["safe_to_report_success"] is True


def test_r6_speaker_updates_include_runtime_truth(task_runtime_service):
    task_runtime_service.loop.executor = CompletingExecutor()
    run = task_runtime_service.create_run(runtime_request())
    completed, _result = task_runtime_service.start(run.run_id)
    service = TaskSpeakerUpdateService(runtime=task_runtime_service)

    update = service.updates(completed.run_id)

    assert update["runtime_truth"]["status"] == "completed"
    assert update["runtime_truth"]["safe_to_report_success"] is True
    assert update["timeline_evidence"]["safe_to_report_success"] is True


def test_r6_firetest_style_five_phase_truth_has_no_divergence(task_runtime_service):
    task_runtime_service.loop.executor = CompletingExecutor()
    task_runtime_service.planner.plan = lambda _request: TaskRunPlan(
        plan_id="task_run_plan_five_phase",
        contract_type="in_chat_final_report",
        status="ready",
        steps=[
            TaskRunStep(step_id="step_01", step_type="validate_runtime", action="validate_runtime"),
            TaskRunStep(step_id="step_02", step_type="run_role_pipeline", action="role_pipeline_run"),
            TaskRunStep(step_id="step_03", step_type="compose_final_result", action="compose_result"),
            TaskRunStep(step_id="step_04", step_type="run_role_pipeline", action="role_pipeline_run"),
            TaskRunStep(step_id="step_05", step_type="compose_final_result", action="compose_result"),
        ],
    )
    run = task_runtime_service.create_run(runtime_request())

    assert len(run.workflow.phases) >= 5

    completed, result = task_runtime_service.start(run.run_id)
    truth = task_runtime_service.get_runtime_truth(completed.run_id)

    assert result.status == "completed"
    assert completed.workflow.status == "completed"
    assert truth.status == "completed"
    assert truth.contradictions == []
    assert truth.safe_to_report_success is True
