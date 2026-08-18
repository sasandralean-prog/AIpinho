from tests.support.runtime_fixtures import runtime_context, runtime_run
from aipinho.services.runtime.task_run_result_service import TaskRunResultService


def test_result_service_omits_raw_content_and_keeps_safe_summary(task_runtime_store):
    run = runtime_run()
    step = run.plan.steps[0]
    step.status = "completed"
    step.output_summary = {"content": "raw log", "safe": "visible"}
    run.status = "completed"
    context = runtime_context(run)

    result = TaskRunResultService(task_runtime_store).build(run, context, events_count=3)

    assert result.safe_to_display is True
    assert result.step_summaries[0]["output_summary"]["content"] == "[omitted_by_task_run_store]"
    assert result.step_summaries[0]["output_summary"]["safe"] == "visible"
    assert result.events_count == 3


def test_result_service_downgrades_completed_when_validation_needs_review(task_runtime_store, monkeypatch):
    class FakeValidation:
        status = "needs_review"
        safe_to_display = True
        validation_id = "validation_test"

        def summary(self):
            return {
                "validation_id": self.validation_id,
                "status": self.status,
                "score": 0.6,
                "safe_to_display": True,
                "warnings": [],
                "blocking_findings": [],
            }

    class FakeValidationGateService:
        def validate_task_run_object(self, run, *, result, events):
            return FakeValidation()

    monkeypatch.setattr("aipinho.services.validation.validation_gate_service.ValidationGateService", FakeValidationGateService)
    run = runtime_run()
    run.status = "completed"
    step = run.plan.steps[0]
    step.status = "completed"
    context = runtime_context(run)

    result = TaskRunResultService(task_runtime_store).build(run, context, events_count=1)

    assert result.status == "partial"
    assert "validation_status:needs_review" in result.limitations
    assert result.validation["status"] == "needs_review"


def test_result_service_uses_governed_summary_for_patch_contract(task_runtime_store, monkeypatch):
    class FakeValidation:
        status = "passed"
        safe_to_display = True
        validation_id = "validation_test"

        def summary(self):
            return {
                "validation_id": self.validation_id,
                "status": self.status,
                "score": 1.0,
                "safe_to_display": True,
                "warnings": [],
                "blocking_findings": [],
            }

    class FakeValidationGateService:
        def validate_task_run_object(self, run, *, result, events):
            return FakeValidation()

    monkeypatch.setattr("aipinho.services.validation.validation_gate_service.ValidationGateService", FakeValidationGateService)
    run = runtime_run()
    run.contract_type = "patch_request"
    run.mode = "governed"
    run.status = "completed"
    run.plan.steps[0].step_type = "execute_patch_pipeline"
    run.plan.steps[0].status = "completed"
    run.plan.steps[0].output_summary = {"status": "no_changes_needed"}
    context = runtime_context(run)

    result = TaskRunResultService(task_runtime_store).build(run, context, events_count=1)

    assert result.status == "completed"
    assert "TaskRun governada concluida" in result.summary
    assert "1 grupo(s) de resultado" in result.summary
    assert result.outputs["patch_result"]["status"] == "no_changes_needed"


def test_result_service_maps_governed_shell_output_to_command_result(task_runtime_store, monkeypatch):
    class FakeValidation:
        status = "passed"
        safe_to_display = True
        validation_id = "validation_shell"

        def summary(self):
            return {
                "validation_id": self.validation_id,
                "status": self.status,
                "score": 1.0,
                "safe_to_display": True,
                "warnings": [],
                "blocking_findings": [],
            }

    class FakeValidationGateService:
        def validate_task_run_object(self, run, *, result, events):
            return FakeValidation()

    monkeypatch.setattr("aipinho.services.validation.validation_gate_service.ValidationGateService", FakeValidationGateService)
    run = runtime_run(action="run_command", contract_type="shell_execution", operation_type="run_command", runtime_profile="shell")
    run.status = "completed"
    run.plan.steps[0].step_type = "execute_governed_shell"
    run.plan.steps[0].action = "run_command"
    run.plan.steps[0].status = "completed"
    run.plan.steps[0].output_summary = {"status": "succeeded", "output": {"exit_code": 0}}
    context = runtime_context(run)

    result = TaskRunResultService(task_runtime_store).build(run, context, events_count=1)

    assert result.status == "completed"
    assert result.outputs["command_result"]["output"]["exit_code"] == 0
    assert result.validation["status"] == "passed"


def test_result_service_failed_run_cannot_keep_passed_validation(task_runtime_store, monkeypatch):
    class FakeValidation:
        status = "passed"
        safe_to_display = True
        validation_id = "validation_structural"

        def summary(self):
            return {
                "validation_id": self.validation_id,
                "status": self.status,
                "score": 1.0,
                "safe_to_display": True,
                "warnings": [],
                "blocking_findings": [],
            }

    class FakeValidationGateService:
        def validate_task_run_object(self, run, *, result, events):
            return FakeValidation()

    monkeypatch.setattr("aipinho.services.validation.validation_gate_service.ValidationGateService", FakeValidationGateService)
    run = runtime_run(action="run_command", contract_type="shell_execution", operation_type="run_command", runtime_profile="shell")
    run.status = "failed"
    run.plan.steps[0].step_type = "execute_governed_shell"
    run.plan.steps[0].action = "run_command"
    run.plan.steps[0].status = "failed"
    run.plan.steps[0].violations = ["FileNotFoundError"]
    context = runtime_context(run)

    result = TaskRunResultService(task_runtime_store).build(run, context, events_count=1)

    assert result.status == "failed"
    assert result.validation["status"] == "failed"
    assert result.validation["score"] == 0.0
    assert "task_run_status:failed" in result.validation["blocking_findings"]
    assert "validation_status:failed" in result.limitations
