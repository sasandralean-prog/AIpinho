from types import SimpleNamespace

from aipinho.schemas.roles.role_pipeline_run import RolePipelineRunRequest
from aipinho.services.roles.role_pipeline_service import RolePipelineService


class _BoundTaskRuns:
    def __init__(self, run_id="task_run_" + "a" * 32):
        self.run_id = run_id
        self.run = SimpleNamespace(
            run_id=run_id,
            operation_id="op_role_test",
            status="running",
            plan=SimpleNamespace(canonical_execution_plan=SimpleNamespace(execution_id="exec_role_test")),
        )

    def get_run_lightweight(self, run_id):
        return self.run if run_id == self.run_id else None


def _bound_request(**kwargs):
    return RolePipelineRunRequest(
        parent_task_run_id="task_run_" + "a" * 32,
        parent_operation_id="op_role_test",
        parent_execution_id="exec_role_test",
        **kwargs,
    )


def _service():
    return RolePipelineService(task_runs=_BoundTaskRuns())


def test_role_pipeline_service_previews_chat_basic_without_model_invocation():
    run = RolePipelineService().preview_pipeline(RolePipelineRunRequest(pipeline_id="chat_basic", user_message="Ola", intent_map={"intent_type": "conversation"}, policy_decision={"status": "allowed"}))
    assert run.status == "preview"
    assert run.final_output["model_invoked"] is False


def test_role_pipeline_service_runs_chat_basic():
    run = _service().run_pipeline(_bound_request(pipeline_id="chat_basic", user_message="Ola", intent_map={"intent_type": "conversation"}, policy_decision={"status": "allowed"}))
    assert run.status == "completed"
    assert run.final_output["real_inference"] is False
    assert run.final_output["tools"] is False


def test_role_pipeline_service_readonly_missing_input_needs_input():
    run = RolePipelineService().preview_pipeline(RolePipelineRunRequest(pipeline_id="readonly_project_report", intent_map={"intent_type": "readonly_analysis"}, policy_decision={"status": "allowed"}))
    assert run.status == "needs_input"


def test_role_pipeline_service_uses_nested_project_report_evidence():
    project_report_response = {
        "status": "completed",
        "report": {
            "report_id": "project_report_test",
            "evidence_index": [
                {
                    "evidence_id": "ev_project_readme",
                    "source": "README.md",
                    "title": "README",
                    "summary": "Project overview evidence.",
                }
            ],
        },
    }

    run = _service().run_pipeline(
        _bound_request(
            pipeline_id="readonly_project_report",
            intent_map={"intent_type": "readonly_analysis"},
            policy_decision={"status": "allowed"},
            project_report=project_report_response,
        )
    )

    supervisor = next(item for item in run.passes if item.pass_id == "supervisor_consistency")
    assert supervisor.status == "completed"
    assert supervisor.input["evidence"][0]["evidence_id"] == "ev_project_readme"


def test_role_pipeline_service_rejects_unbound_real_execution():
    run = RolePipelineService().run_pipeline(
        RolePipelineRunRequest(
            pipeline_id="chat_basic",
            user_message="Ola",
            intent_map={"intent_type": "conversation"},
            policy_decision={"status": "allowed"},
        )
    )
    assert run.status == "rejected"
    assert "ROLE_PIPELINE_TASKRUN_BINDING_REQUIRED" in run.warnings
    assert run.authority_mode == "preview_only"
    assert run.final_output["reason_code"] == "ROLE_PIPELINE_TASKRUN_BINDING_REQUIRED"
