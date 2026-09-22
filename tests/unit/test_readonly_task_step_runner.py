from types import SimpleNamespace

from tests.support.runtime_fixtures import runtime_context, runtime_run
from aipinho.schemas.runtime.task_run_step import TaskRunStep
from aipinho.services.runtime.readonly_task_step_runner import ReadOnlyTaskStepRunner


class HealthyDependency:
    def status(self):
        return {"status": "ok"}


class DisabledDependency:
    def status(self):
        return {"status": "disabled"}



def test_file_context_semantic_outcome_marks_partial_context_safe_with_limitations():
    runner = ReadOnlyTaskStepRunner()
    bundle = SimpleNamespace(
        status="partial",
        warnings=["file_selection_partial"],
        violations=[],
        omitted_files=[SimpleNamespace(path="src/omitted.kt")],
    )

    semantic = runner._file_context_semantic_outcome(bundle)

    assert semantic["use_safety"]["safe_for_downstream_static_analysis"] == (
        "true_with_limitations"
    )
    assert "file_context_budget_or_omissions" in semantic["limitations"]
    assert "file_context_omitted_files_present" in semantic["limitations"]
    assert semantic["missing_truth"] == []


def test_file_context_semantic_outcome_marks_complete_context_fully_safe():
    runner = ReadOnlyTaskStepRunner()
    bundle = SimpleNamespace(
        status="ok",
        warnings=[],
        violations=[],
        omitted_files=[],
    )

    semantic = runner._file_context_semantic_outcome(bundle)

    assert semantic["use_safety"]["safe_for_downstream_static_analysis"] is True
    assert semantic["limitations"] == []
    assert semantic["missing_truth"] == []


def test_file_context_semantic_outcome_marks_blocked_context_unsafe():
    runner = ReadOnlyTaskStepRunner()
    bundle = SimpleNamespace(
        status="blocked",
        warnings=[],
        violations=["context_build_failed"],
        omitted_files=[],
    )

    semantic = runner._file_context_semantic_outcome(bundle)

    assert semantic["use_safety"]["safe_for_downstream_static_analysis"] is False
    assert semantic["missing_truth"] == ["context_build_failed"]



def test_project_analysis_semantic_outcome_marks_partial_report_safe_with_limitations():
    runner = ReadOnlyTaskStepRunner()
    result = SimpleNamespace(
        status="partial",
        safe_to_continue=True,
        warnings=["file_selection_partial"],
        limitations=["analysis_scope_partial"],
        violations=[],
    )

    semantic = runner._project_analysis_semantic_outcome(result)

    assert semantic["use_safety"]["safe_for_user_report"] == (
        "true_with_limitations"
    )
    assert "file_selection_partial" in semantic["limitations"]
    assert "analysis_scope_partial" in semantic["limitations"]
    assert "project_analysis_partial" in semantic["limitations"]
    assert semantic["missing_truth"] == []


def test_project_analysis_semantic_outcome_marks_complete_report_safe():
    runner = ReadOnlyTaskStepRunner()
    result = SimpleNamespace(
        status="ok",
        safe_to_continue=True,
        warnings=[],
        limitations=[],
        violations=[],
    )

    semantic = runner._project_analysis_semantic_outcome(result)

    assert semantic["use_safety"]["safe_for_user_report"] is True
    assert semantic["limitations"] == []
    assert semantic["missing_truth"] == []


def test_project_analysis_semantic_outcome_marks_unsafe_result_not_reportable():
    runner = ReadOnlyTaskStepRunner()
    result = SimpleNamespace(
        status="failed",
        safe_to_continue=False,
        warnings=[],
        limitations=[],
        violations=["analysis_failed"],
    )

    semantic = runner._project_analysis_semantic_outcome(result)

    assert semantic["use_safety"]["safe_for_user_report"] is False
    assert semantic["missing_truth"] == ["analysis_failed"]


def test_step_runner_blocks_unknown_step_type():
    run = runtime_run()
    context = runtime_context(run)
    step = TaskRunStep(step_id="step_unknown", step_type="unknown", action="validate_runtime")

    outcome = ReadOnlyTaskStepRunner().run(run, step, context)

    assert outcome.status == "blocked"
    assert "unknown_task_step" in outcome.violations


def test_step_runner_validate_runtime_accepts_ok_or_disabled_dependencies():
    run = runtime_run()
    context = runtime_context(run)
    runner = ReadOnlyTaskStepRunner(
        readonly=HealthyDependency(),
        analysis=HealthyDependency(),
        reports=DisabledDependency(),
        roles=HealthyDependency(),
    )

    outcome = runner.run(run, run.plan.steps[0], context)

    assert outcome.status == "completed"
    assert outcome.summary["components"]["reports"] == "disabled"


def test_evidence_repair_request_preserves_focus_paths_from_continuation() -> None:
    runner = ReadOnlyTaskStepRunner()
    run = runtime_run()
    run.intent_map = {
        **dict(run.intent_map or {}),
        "mission_continuation": {
            "evidence_repair": {
                "required": True,
                "focus_paths": ["src/A.kt", "src/B.kt"],
            }
        },
    }

    request = runner._request(run)

    assert request.goal == "evidence_repair_analysis"
    assert request.focus_paths == ["src/A.kt", "src/B.kt"]
    assert "Evidence repair" in request.prompt


def test_evidence_repair_marks_destructive_use_safe_only_when_focus_is_fully_resolved() -> None:
    runner = ReadOnlyTaskStepRunner()
    result = SimpleNamespace(
        status="partial",
        safe_to_continue=True,
        warnings=["other_project_file_omitted"],
        limitations=["analysis_scope_partial"],
        violations=[],
        file_context=SimpleNamespace(
            items=[
                SimpleNamespace(
                    path="src/A.kt",
                    status="included",
                    content_truncated=False,
                ),
                SimpleNamespace(
                    path="src/B.kt",
                    status="included",
                    content_truncated=False,
                ),
            ]
        ),
    )

    semantic = runner._project_analysis_semantic_outcome(
        result,
        repair={
            "required": True,
            "focus_paths": ["src/A.kt", "src/B.kt"],
        },
    )

    assert (
        semantic["use_safety"]["safe_for_destructive_action"]
        is True
    )
    assert (
        semantic["semantic_properties"][
            "evidence_repair_focus_complete"
        ]
        is True
    )
    assert semantic["semantic_properties"][
        "evidence_repair_unresolved_paths"
    ] == []


def test_evidence_repair_does_not_promote_destructive_safety_when_focus_is_missing() -> None:
    runner = ReadOnlyTaskStepRunner()
    result = SimpleNamespace(
        status="partial",
        safe_to_continue=True,
        warnings=[],
        limitations=[],
        violations=[],
        file_context=SimpleNamespace(
            items=[
                SimpleNamespace(
                    path="src/A.kt",
                    status="included",
                    content_truncated=False,
                )
            ]
        ),
    )

    semantic = runner._project_analysis_semantic_outcome(
        result,
        repair={
            "required": True,
            "focus_paths": ["src/A.kt", "src/B.kt"],
        },
    )

    assert (
        semantic["use_safety"]["safe_for_destructive_action"]
        is False
    )
    assert semantic["semantic_properties"][
        "evidence_repair_unresolved_paths"
    ] == ["src/B.kt"]
    assert "evidence_repair_focus_unresolved" in semantic["limitations"]
