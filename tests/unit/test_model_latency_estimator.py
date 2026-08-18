from aipinho.services.models.model_latency_estimator import ModelLatencyEstimator
from aipinho.services.models.model_registry_service import ModelRegistryService


def test_model_latency_estimator_warns_for_large_cpu_model():
    model = ModelRegistryService().get_runtime_model("deepseek_r1_distill_qwen_14b_q4_k_m")
    estimate = ModelLatencyEstimator().estimate(model)
    assert estimate.latency_class == "very_high"
    assert estimate.requires_warning is True
