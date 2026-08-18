from aipinho.schemas.roles.role_pipeline import RolePipeline, RolePipelinePassDefinition
from aipinho.schemas.roles.role_pipeline_run import RolePipelineRun, RolePipelineRunRequest
from aipinho.schemas.roles.role_pipeline_trace import RolePipelineTraceItem


def test_role_pipeline_contracts_construct():
    pipeline = RolePipeline(pipeline_id="p", passes=[RolePipelinePassDefinition(pass_id="a", role_id="speaker")])
    assert pipeline.passes[0].required is True
    request = RolePipelineRunRequest(pipeline_id="p")
    assert request.model_mode == "stub"
    run = RolePipelineRun(pipeline_id="p")
    run.trace.append(RolePipelineTraceItem(stage="x", status="ok"))
    assert run.trace[0].stage == "x"
