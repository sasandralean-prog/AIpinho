from aipinho.services.models.model_hardware_estimator import ModelHardwareEstimator
from aipinho.services.models.model_registry_service import ModelRegistryService


def test_model_hardware_estimator_marks_14b_manual_only():
    model = ModelRegistryService().get_runtime_model("qwen2_5_coder_14b_q5_k_m")
    estimate = ModelHardwareEstimator().estimate(model)
    assert estimate.hardware_class == "large_cpu_slow"
    assert estimate.manual_only is True
