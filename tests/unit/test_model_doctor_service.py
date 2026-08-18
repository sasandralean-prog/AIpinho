from aipinho.schemas.models.model_doctor_request import ModelDoctorRequest
from aipinho.services.models.model_doctor_service import ModelDoctorService


def test_model_doctor_runs_metadata_checks_without_loading_model(tmp_path):
    service = ModelDoctorService(store_dir=tmp_path)
    result = service.run_for_model("qwen2_5_coder_7b_q4_k_m", ModelDoctorRequest(include_trace=False))
    assert result is not None
    assert result.model_id == "qwen2_5_coder_7b_q4_k_m"
    assert "first_token_probe_requires_operator_confirmation" not in result.blocked_reasons
    assert {check.name for check in result.checks}.issuperset({"model_path", "model_security", "load_probe"})
