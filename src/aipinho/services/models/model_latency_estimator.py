from __future__ import annotations

from aipinho.core.paths import PATHS
from aipinho.schemas.models.model_definition import ModelDefinition
from aipinho.schemas.models.model_latency_profile import ModelLatencyProfile
from aipinho.utils.yaml_loader import load_yaml_file


class ModelLatencyEstimator:
    def __init__(self) -> None:
        self.config = load_yaml_file(PATHS.config_root / "models" / "model_latency_policy.yaml", critical=True, root=PATHS.config_root / "models")

    def estimate(self, model: ModelDefinition) -> ModelLatencyProfile:
        hardware_class = model.hardware_class or ("large_cpu_slow" if model.parameter_class == "14b" else "medium_cpu")
        latency = self.config.get("latency", {}) if isinstance(self.config.get("latency", {}), dict) else {}
        details = latency.get(hardware_class, {}) if isinstance(latency.get(hardware_class, {}), dict) else {}
        return ModelLatencyProfile(
            model_id=model.model_id,
            latency_class=str(details.get("class", "unknown")),
            expected=str(details.get("expected", "unknown")),
            requires_warning=bool(model.latency_warning_required or details.get("requires_warning", False)),
        )
