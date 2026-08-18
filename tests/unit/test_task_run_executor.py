from types import SimpleNamespace

from tests.support.runtime_fixtures import runtime_context, runtime_run

from aipinho.services.runtime.readonly_task_step_runner import TaskStepOutcome
from aipinho.services.runtime.task_no_change_evidence_service import NoChangeEvidence
from aipinho.services.runtime.governed_task_step_runner import GovernedTaskStepRunner
from aipinho.services.runtime.task_run_executor import TaskRunExecutor
from aipinho.services.patching.patch_planning_service import PatchPlanningService
from patch_fixtures import patch_request, patch_workspace


class FakeRunner:
    def __init__(self):
        self.calls = []

    def run(self, run, step, context):
        self.calls.append((run.run_id, step.step_id))
        return TaskStepOutcome(status="completed", summary={"ok": True})

    def status(self):
        return {"status": "ok"}


def test_executor_delegates_to_configured_runner():
    fake = FakeRunner()
    run = runtime_run()
    context = runtime_context(run)

    outcome = TaskRunExecutor(runner=fake).execute_step(run, run.plan.steps[0], context)

    assert outcome.status == "completed"
    assert fake.calls == [(run.run_id, "step_01")]


def test_default_executor_uses_governed_runner():
    status = TaskRunExecutor().status()

    assert status["mode"] == "governed"
    assert status["runner"]["service"] == "governed_task_step_runner"


def test_patch_pipeline_step_is_known_even_without_targetable_plan():
    run = runtime_run(
        contract_type="patch_request",
        operation_type="patch_preview",
        action="apply_patch",
    ).model_copy(
        update={
            "intent_map": {
                "raw_prompt": "Corrija o problema usando um patch minimo quando houver alvo editavel."
            }
        }
    )
    step = run.plan.steps[0].model_copy(
        update={
            "step_id": "step_patch",
            "step_type": "execute_patch_pipeline",
            "title": "Execute governed patch pipeline",
        }
    )
    context = runtime_context(run)

    outcome = TaskRunExecutor().execute_step(run, step, context)

    assert outcome.status == "blocked"
    assert "patch_plan_missing" in outcome.violations
    assert "unknown_task_step" not in outcome.violations


def test_patch_pipeline_uses_model_planner_when_local_action_is_not_targetable():
    class FakeNoChangeEvidence:
        def evaluate(self, *, prompt, workspace):
            return None

    class FakeLocalActions:
        def run_explicit_modify_file(self, **kwargs):
            return None

        def run_inferred_ui_text_update(self, **kwargs):
            return None

    class FakePlan:
        plan_id = "patch_plan_model"
        status = "ready_for_review"
        quality_gate = {}

        def model_dump(self):
            return {"plan_id": self.plan_id, "status": self.status}

    class FakeModelPlanner:
        def create_plan(self, **kwargs):
            from types import SimpleNamespace

            return SimpleNamespace(
                status="ready",
                plan=FakePlan(),
                model_run_id="role_model_run_test",
                model_id="fake-model",
                provider_id="fake-provider",
                warnings=[],
                blocked_reasons=[],
            )

    runner = GovernedTaskStepRunner(
        local_actions=FakeLocalActions(),
        no_change_evidence=FakeNoChangeEvidence(),
        model_patch_planner=FakeModelPlanner(),
    )
    runner._agent_run_id = lambda run, operation_type: "agent_run_test"
    run = runtime_run(contract_type="patch_request", operation_type="patch_preview", action="apply_patch").model_copy(
        update={"workspace": "C:/workspace", "intent_map": {"raw_prompt": "Prepare a patch preview."}}
    )
    step = run.plan.steps[0].model_copy(update={"step_type": "execute_patch_pipeline"})

    outcome = runner.run(run, step, runtime_context(run))

    assert outcome.status == "completed"
    assert outcome.summary["status"] == "patch_preview_created"


def test_patch_pipeline_applies_bound_patch_plan_through_governed_tool_gateway(tmp_path):
    workspace = patch_workspace(tmp_path)
    plan = PatchPlanningService().create_plan(patch_request(workspace)).plan

    class FakeToolGateway:
        def __init__(self):
            self.calls = []

        def invoke(self, _agent_id, _run_id, tool_name, request):
            self.calls.append((tool_name, request))
            path = request.path_ref
            if tool_name == "modify_file":
                path_obj = __import__("pathlib").Path(path)
                path_obj.write_text(str(request.input["content"]), encoding="utf-8")
            return SimpleNamespace(
                status="succeeded",
                tool_invocation=SimpleNamespace(tool_invocation_id="tool_patch_1", error_code=None, block_reason_code=None),
                policy_decision=SimpleNamespace(decision="allow", reason_code="approved_execution_plan"),
                output={"file_path_sanitized": path, "hash": "hash"},
                validation_result=None,
                artifacts=[],
            )

    class FakeLocalActions:
        def __init__(self):
            self.tool_gateway = FakeToolGateway()

        def infer_workspace_id(self, workspace_context):
            return f"workspace:{workspace_context}"

    actions = FakeLocalActions()
    runner = GovernedTaskStepRunner(local_actions=actions)
    runner._agent_run_id = lambda _run, _operation_type: "agent_run_patch"
    run = runtime_run(
        contract_type="patch_request",
        operation_type="patch_apply",
        runtime_profile="patch",
        action="apply_patch",
        workspace=str(workspace),
    ).model_copy(
        update={
            "approval_id": "approval_test",
            "intent_map": {"patch_plan": plan.model_dump(mode="json")},
        }
    )
    run.current_step_id = "step_01"
    run.plan.canonical_execution_plan.execution_steps[0].inputs["patch_plan"] = plan.model_dump(mode="json")
    context = runtime_context(run)

    outcome = runner._execute_patch_pipeline(run, context)
    validation = runner._validate_patch_result(run, context)

    assert outcome.status == "completed"
    assert outcome.summary["status"] == "patch_applied"
    assert validation.status == "completed"
    assert (workspace / "docs" / "note.md").read_text(encoding="utf-8").strip() == "# New"
    assert actions.tool_gateway.calls[0][0] == "modify_file"


def test_positive_prior_evidence_precedes_modify_attempt_for_report_output():
    class FakeNoChangeEvidence:
        def evaluate(self, *, prompt, workspace):
            return NoChangeEvidence(
                status="no_changes_needed",
                reason_code="validated_state_already_satisfies_request",
                report_path="reports/diagnosis.md",
                verdict="capability_implemented",
                summary="Prior validation confirms the requested capability.",
                evidence_refs=["file:reports/diagnosis.md"],
            )

    class FakeLocalActions:
        def __init__(self):
            self.modify_calls = 0
            self.create_calls = 0

        def run_explicit_modify_file(self, **kwargs):
            self.modify_calls += 1
            raise AssertionError("modify must not run after positive no-change evidence")

        def run_inferred_ui_text_update(self, **kwargs):
            raise AssertionError("UI inference must not run after positive no-change evidence")

        def run_explicit_create_file(self, **kwargs):
            self.create_calls += 1
            return None

    actions = FakeLocalActions()
    runner = GovernedTaskStepRunner(local_actions=actions, no_change_evidence=FakeNoChangeEvidence())
    runner._agent_run_id = lambda run, operation_type: "agent_run_test"
    run = runtime_run(
        contract_type="patch_request",
        operation_type="patch_preview",
        action="apply_patch",
    ).model_copy(
        update={
            "workspace": "C:/workspace",
            "intent_map": {
                "raw_prompt": "Use the prior diagnosis and write the final report to reports/fix.md."
            },
        }
    )
    step = run.plan.steps[0].model_copy(
        update={"step_id": "step_patch", "step_type": "execute_patch_pipeline"}
    )
    context = runtime_context(run)

    outcome = runner.run(run, step, context)

    assert outcome.status == "completed"
    assert outcome.summary["status"] == "no_changes_needed"
    assert actions.modify_calls == 0
    assert actions.create_calls == 1
