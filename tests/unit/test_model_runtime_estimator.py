from aipinho.services.models.model_runtime_estimator import ModelRuntimeEstimator


def test_model_runtime_estimator_with_size_has_estimate():
    estimate = ModelRuntimeEstimator().estimate(model_size_bytes=4 * 1024**3, ctx_size=2048, n_predict=256, quantization="q4")
    assert estimate.estimated_ram_gb > 4
    assert estimate.confidence == "medium"


def test_model_runtime_estimator_unknown_size_low_confidence():
    estimate = ModelRuntimeEstimator().estimate(model_size_bytes=None)
    assert estimate.confidence == "low"
    assert "model_size_unknown" in estimate.warnings


def test_model_runtime_estimator_warns_above_threshold():
    estimate = ModelRuntimeEstimator(config={"memory": {"warn_if_estimated_ram_gb_above": 1, "max_estimated_ram_gb": 99}}).estimate(model_size_bytes=2 * 1024**3)
    assert "estimated_ram_above_warning_threshold" in estimate.warnings
