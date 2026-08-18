from aipinho.schemas.roles.role_pipeline_run import RolePipelineRunRequest
from aipinho.services.roles.role_pipeline_planner import RolePipelinePlanner


def test_role_pipeline_planner_choose_chat_basic():
    assert RolePipelinePlanner().choose_pipeline(RolePipelineRunRequest(intent_map={"intent_type": "conversation"})) == "chat_basic"


def test_role_pipeline_planner_choose_readonly_project_report():
    assert RolePipelinePlanner().choose_pipeline(RolePipelineRunRequest(intent_map={"intent_type": "readonly_analysis"})) == "readonly_project_report"


def test_role_pipeline_planner_choose_task_preview():
    assert RolePipelinePlanner().choose_pipeline(RolePipelineRunRequest(intent_map={"intent_type": "patch_request"})) == "task_preview"
