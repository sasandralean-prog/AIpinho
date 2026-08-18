from aipinho.services.validation.role_pipeline_validator import RolePipelineValidator
from validation_fixtures import valid_role_pipeline_run


def test_role_pipeline_validator_accepts_valid_run():
    assert RolePipelineValidator().validate(valid_role_pipeline_run()) == []


def test_role_pipeline_validator_rejects_missing_evaluation():
    run = valid_role_pipeline_run()
    run["passes"][0]["evaluation_result"] = {}
    findings = RolePipelineValidator().validate(run)
    assert any(item.code == "missing_evaluation" for item in findings)


def test_role_pipeline_validator_accepts_real_inference_when_policy_allows():
    run = valid_role_pipeline_run()
    run["passes"][0]["model_response"]["real_inference"] = True
    findings = RolePipelineValidator().validate(run)
    assert not any(item.code == "real_inference_auto_use" for item in findings)
