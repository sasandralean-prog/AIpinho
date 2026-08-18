from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.schemas.models.model_doctor_result import ModelDoctorResult
from aipinho.services.models.model_registry_service import ModelRegistryService


def test_registered_models_validate_against_model_definition_schema():
    for model in ModelRegistryService().runtime_models():
        assert isinstance(ModelDefinition(**model.model_dump()), ModelDefinition)


def test_model_doctor_result_schema_requires_status_and_checks():
    result = ModelDoctorResult(
        doctor_run_id="doctor_test",
        model_id="m",
        status="healthy",
        checks=[],
        created_at="2026-06-07T00:00:00+00:00",
    )
    assert result.status == "healthy"
