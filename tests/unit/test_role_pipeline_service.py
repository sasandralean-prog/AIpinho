from aipinho.schemas.roles.role_pipeline_run import RolePipelineRunRequest
from aipinho.services.roles.role_pipeline_service import RolePipelineService


def test_role_pipeline_service_previews_chat_basic_without_model_invocation():
    run = RolePipelineService().preview_pipeline(RolePipelineRunRequest(pipeline_id="chat_basic", user_message="Ola", intent_map={"intent_type": "conversation"}, policy_decision={"status": "allowed"}))
    assert run.status == "preview"
    assert run.final_output["model_invoked"] is False


def test_role_pipeline_service_runs_chat_basic():
    run = RolePipelineService().run_pipeline(RolePipelineRunRequest(pipeline_id="chat_basic", user_message="Ola", intent_map={"intent_type": "conversation"}, policy_decision={"status": "allowed"}))
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

    run = RolePipelineService().run_pipeline(
        RolePipelineRunRequest(
            pipeline_id="readonly_project_report",
            intent_map={"intent_type": "readonly_analysis"},
            policy_decision={"status": "allowed"},
            project_report=project_report_response,
        )
    )

    analyst = next(item for item in run.passes if item.pass_id == "analyst_findings")
    assert analyst.status == "completed"
    assert "required_pass_failed:analyst_findings" not in run.warnings
